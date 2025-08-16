#!/usr/bin/env python3
"""
Test script for WebDriver concurrency improvements
"""
import sys
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_forum.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

import threading
import time
from forum.tasks import create_webdriver_with_cleanup

def test_webdriver_creation(thread_id):
    """Test creating WebDriver instances concurrently"""
    try:
        print(f"Thread {thread_id}: Starting WebDriver creation...")
        driver, user_data_dir = create_webdriver_with_cleanup()
        print(f"Thread {thread_id}: Successfully created WebDriver with dir: {user_data_dir}")
        
        # Test basic functionality
        driver.get("https://www.google.com")
        title = driver.title
        print(f"Thread {thread_id}: Page title: {title}")
        
        # Clean up
        driver.quit()
        print(f"Thread {thread_id}: WebDriver cleaned up successfully")
        
    except Exception as e:
        print(f"Thread {thread_id}: Error - {e}")

def run_concurrency_test():
    """Run multiple WebDriver instances concurrently"""
    print("Starting WebDriver concurrency test...")
    
    threads = []
    for i in range(3):  # Test 3 concurrent instances
        thread = threading.Thread(target=test_webdriver_creation, args=(i,))
        threads.append(thread)
    
    # Start all threads
    start_time = time.time()
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    print(f"Concurrency test completed in {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    run_concurrency_test()
