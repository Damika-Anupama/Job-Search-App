#!/usr/bin/env python3
"""
Service monitoring script for Job Search Application.

This script checks the health of all services and provides a comprehensive
status report. Can be used for monitoring and alerting.
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
import subprocess
import os

class ServiceMonitor:
    """Monitor all application services"""
    
    def __init__(self):
        self.services = {
            'backend': 'http://localhost:8000/health',
            'frontend': 'http://localhost:8501/_stcore/health',
            'redis': None,  # Will use docker inspect
        }
        self.docker_services = [
            'job-search-backend',
            'job-search-frontend', 
            'job-search-worker',
            'job-search-scheduler',
            'job-search-redis'
        ]
    
    def check_http_service(self, name: str, url: str) -> Dict[str, Any]:
        """Check HTTP service health"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'details': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:100]
                }
            else:
                return {
                    'status': 'unhealthy', 
                    'error': f'HTTP {response.status_code}',
                    'details': response.text[:100]
                }
        except requests.exceptions.ConnectioError:
            return {'status': 'unreachable', 'error': 'Connection refused'}
        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': 'Request timeout'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_docker_service(self, container_name: str) -> Dict[str, Any]:
        """Check Docker container health"""
        try:
            # Check if container is running
            result = subprocess.run(
                ['docker', 'inspect', container_name, '--format', '{{.State.Status}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                status = result.stdout.strip()
                
                # Get additional info
                health_result = subprocess.run(
                    ['docker', 'inspect', container_name, '--format', '{{.State.Health.Status}}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                health_status = health_result.stdout.strip() if health_result.returncode == 0 else 'unknown'
                
                return {
                    'status': 'healthy' if status == 'running' else 'unhealthy',
                    'container_status': status,
                    'health_status': health_status,
                    'details': f'Container: {status}, Health: {health_status}'
                }
            else:
                return {'status': 'not_found', 'error': 'Container not found'}
                
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'error': 'Docker command timeout'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_celery_worker(self) -> Dict[str, Any]:
        """Check Celery worker status"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'job-search-worker', 'celery', '-A', 'src.job_search.scraping.tasks.celery_app', 'inspect', 'ping'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and 'OK' in result.stdout:
                return {'status': 'healthy', 'details': 'Worker responding to ping'}
            else:
                return {'status': 'unhealthy', 'error': 'Worker not responding', 'details': result.stderr}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_celery_scheduler(self) -> Dict[str, Any]:
        """Check Celery Beat scheduler status"""
        try:
            # Check if beat process is running in scheduler container
            result = subprocess.run(
                ['docker', 'exec', 'job-search-scheduler', 'ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and 'celery beat' in result.stdout:
                return {'status': 'healthy', 'details': 'Scheduler process running'}
            else:
                return {'status': 'unhealthy', 'error': 'Beat process not found'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'services': {},
            'summary': {
                'healthy': 0,
                'unhealthy': 0,
                'errors': 0
            }
        }
        
        print("🔍 Running service health check...")
        
        # Check HTTP services
        for name, url in self.services.items():
            if url:
                print(f"  Checking {name}...")
                results['services'][name] = self.check_http_service(name, url)
        
        # Check Docker containers
        for container in self.docker_services:
            print(f"  Checking container {container}...")
            results['services'][container] = self.check_docker_service(container)
        
        # Check Celery services specifically
        print("  Checking Celery worker...")
        results['services']['celery_worker'] = self.check_celery_worker()
        
        print("  Checking Celery scheduler...")
        results['services']['celery_scheduler'] = self.check_celery_scheduler()
        
        # Calculate summary
        for service, status in results['services'].items():
            if status['status'] == 'healthy':
                results['summary']['healthy'] += 1
            elif status['status'] in ['unhealthy', 'unreachable', 'timeout', 'not_found']:
                results['summary']['unhealthy'] += 1
                results['overall_status'] = 'degraded'
            else:
                results['summary']['errors'] += 1
                results['overall_status'] = 'unhealthy'
        
        return results
    
    def print_report(self, results: Dict[str, Any]):
        """Print formatted health check report"""
        status_emoji = {
            'healthy': '✅',
            'unhealthy': '❌', 
            'degraded': '⚠️',
            'unreachable': '🔌',
            'timeout': '⏰',
            'error': '💥',
            'not_found': '❓'
        }
        
        print(f"\n📊 Service Health Report - {results['timestamp']}")
        print("=" * 60)
        
        overall_emoji = status_emoji.get(results['overall_status'], '❓')
        print(f"Overall Status: {overall_emoji} {results['overall_status'].upper()}")
        
        print(f"\nSummary: ✅ {results['summary']['healthy']} healthy, " + 
              f"❌ {results['summary']['unhealthy']} unhealthy, " +
              f"💥 {results['summary']['errors']} errors")
        
        print("\nService Details:")
        print("-" * 40)
        
        for service, status in results['services'].items():
            emoji = status_emoji.get(status['status'], '❓')
            print(f"{emoji} {service:20} {status['status']:12} {status.get('details', status.get('error', ''))}")
        
        if results['overall_status'] != 'healthy':
            print(f"\n⚠️  System is {results['overall_status']}. Check failed services above.")
        else:
            print(f"\n🎉 All services are healthy!")

def main():
    """Main monitoring function"""
    monitor = ServiceMonitor()
    
    # Support command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--json':
            # JSON output for scripts/monitoring tools
            results = monitor.run_health_check()
            print(json.dumps(results, indent=2))
            sys.exit(0 if results['overall_status'] == 'healthy' else 1)
        elif sys.argv[1] == '--continuous':
            # Continuous monitoring mode
            print("Starting continuous monitoring (Ctrl+C to stop)...")
            try:
                while True:
                    results = monitor.run_health_check()
                    monitor.print_report(results)
                    print(f"\nNext check in 60 seconds...")
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped.")
                sys.exit(0)
    
    # Default: single check with formatted output
    results = monitor.run_health_check()
    monitor.print_report(results)
    
    # Exit with error code if system is unhealthy
    sys.exit(0 if results['overall_status'] == 'healthy' else 1)

if __name__ == '__main__':
    main()