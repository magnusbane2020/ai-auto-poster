"""
db_monitor.py - Database health monitoring and self-healing utilities.
Monitors database status, detects issues, and automatically repairs common problems.
"""
import os
import time
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple
from db import get_connection, _cleanup_locks, checkpoint_wal, CFG, log_event

class DatabaseMonitor:
    """
    Monitors database health and performs self-healing operations.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or CFG["DB_PATH"]
        self.lock_files = [f"{self.db_path}-wal", f"{self.db_path}-shm"]
        self.health_history = []
    
    def check_health(self, verbose: bool = True) -> Dict[str, any]:
        """
        Perform comprehensive database health check.
        
        Args:
            verbose: Print detailed output
        Returns:
            Health status dictionary
        """
        health = {
            "timestamp": datetime.now().isoformat(),
            "healthy": True,
            "issues": [],
            "warnings": [],
            "stats": {}
        }
        
        if verbose:
            print("\n" + "="*60)
            print("🔍 DATABASE HEALTH CHECK")
            print("="*60)
        
        # 1. Check if database file exists
        if not os.path.exists(self.db_path):
            health["healthy"] = False
            health["issues"].append("Database file not found")
            if verbose:
                print(f"❌ Database file: NOT FOUND ({self.db_path})")
            return health
        
        size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        health["stats"]["size_mb"] = round(size_mb, 2)
        if verbose:
            print(f"✅ Database file: {self.db_path} ({size_mb:.2f} MB)")
        
        # 2. Check lock files
        lock_status = {}
        for lock_file in self.lock_files:
            if os.path.exists(lock_file):
                size_kb = os.path.getsize(lock_file) / 1024
                lock_status[lock_file] = {"exists": True, "size_kb": round(size_kb, 2)}
                if verbose:
                    print(f"⚠️  Lock file: {lock_file} ({size_kb:.2f} KB)")
            else:
                lock_status[lock_file] = {"exists": False}
                if verbose:
                    print(f"✅ Lock file: {lock_file} (clear)")
        
        health["stats"]["lock_files"] = lock_status
        
        # 3. Try to connect and check journal mode
        try:
            conn = get_connection()
            
            # Check journal mode
            cursor = conn.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            health["stats"]["journal_mode"] = mode
            
            if mode != "wal":
                health["warnings"].append(f"Journal mode is '{mode}', expected 'wal'")
                if verbose:
                    print(f"⚠️  Journal mode: {mode} (expected: wal)")
            else:
                if verbose:
                    print(f"✅ Journal mode: {mode}")
            
            # Check integrity
            cursor = conn.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            health["stats"]["integrity"] = integrity
            
            if integrity != "ok":
                health["healthy"] = False
                health["issues"].append(f"Integrity check failed: {integrity}")
                if verbose:
                    print(f"❌ Integrity: {integrity}")
            else:
                if verbose:
                    print(f"✅ Integrity: OK")
            
            # Check table counts
            tables = ["posts", "topics", "ai_cache", "costs", "logs"]
            counts = {}
            
            for table in tables:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    counts[table] = count
                    if verbose:
                        print(f"   - {table}: {count} rows")
                except Exception as e:
                    health["issues"].append(f"Failed to count {table}: {str(e)}")
                    if verbose:
                        print(f"   - {table}: ERROR ({str(e)})")
            
            health["stats"]["table_counts"] = counts
            
            # Check for stale data or anomalies
            cursor = conn.execute("""
                SELECT COUNT(*) FROM posts 
                WHERE status = 'scheduled' AND scheduled_at < datetime('now', '-7 days')
            """)
            stale_posts = cursor.fetchone()[0]
            
            if stale_posts > 0:
                health["warnings"].append(f"{stale_posts} posts scheduled over 7 days ago")
                if verbose:
                    print(f"⚠️  Stale scheduled posts: {stale_posts}")
            
            # Check cache size
            cursor = conn.execute("SELECT COUNT(*) FROM ai_cache")
            cache_size = cursor.fetchone()[0]
            
            if cache_size > 10000:
                health["warnings"].append(f"Large cache size: {cache_size} entries")
                if verbose:
                    print(f"⚠️  AI cache large: {cache_size} entries (consider cleanup)")
            
            conn.close()
            
            if verbose:
                print("\n" + "="*60)
                if health["healthy"] and len(health["warnings"]) == 0:
                    print("✅ DATABASE HEALTHY - No issues detected")
                elif health["healthy"] and len(health["warnings"]) > 0:
                    print(f"⚠️  DATABASE OK - {len(health['warnings'])} warnings")
                else:
                    print(f"❌ DATABASE UNHEALTHY - {len(health['issues'])} critical issues")
                print("="*60 + "\n")
            
        except Exception as e:
            health["healthy"] = False
            health["issues"].append(f"Connection failed: {str(e)}")
            if verbose:
                print(f"❌ Database connection: FAILED ({str(e)})")
                print("\n" + "="*60)
                print("❌ DATABASE UNHEALTHY - Cannot connect")
                print("="*60 + "\n")
        
        # Log health check
        log_event("db_monitor", "info" if health["healthy"] else "error", 
                 "Database health check completed",
                 {"healthy": health["healthy"], "issues": health["issues"], "warnings": health["warnings"]})
        
        # Store in history
        self.health_history.append(health)
        if len(self.health_history) > 100:  # Keep last 100 checks
            self.health_history.pop(0)
        
        return health
    
    def self_heal(self, verbose: bool = True) -> Dict[str, any]:
        """
        Attempt to automatically fix common database issues.
        
        Args:
            verbose: Print detailed output
        Returns:
            Healing report dictionary
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "actions": [],
            "success": True
        }
        
        if verbose:
            print("\n" + "="*60)
            print("🩺 DATABASE SELF-HEALING")
            print("="*60)
        
        # Check health first
        health = self.check_health(verbose=False)
        
        # Action 1: Clean up stale lock files
        locks_cleaned = False
        for lock_file in self.lock_files:
            if os.path.exists(lock_file):
                try:
                    # Try to checkpoint first
                    checkpoint_wal()
                    time.sleep(0.5)
                    
                    # Then try to remove
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        report["actions"].append(f"Removed stale lock file: {lock_file}")
                        locks_cleaned = True
                        if verbose:
                            print(f"✅ Cleaned: {lock_file}")
                except Exception as e:
                    report["actions"].append(f"Failed to remove {lock_file}: {str(e)}")
                    report["success"] = False
                    if verbose:
                        print(f"❌ Failed to clean {lock_file}: {str(e)}")
        
        if not locks_cleaned and verbose:
            print("✅ No stale lock files to clean")
        
        # Action 2: Force WAL checkpoint
        try:
            checkpoint_wal()
            report["actions"].append("WAL checkpoint completed")
            if verbose:
                print("✅ WAL checkpoint completed")
        except Exception as e:
            report["actions"].append(f"WAL checkpoint failed: {str(e)}")
            if verbose:
                print(f"⚠️  WAL checkpoint failed: {str(e)}")
        
        # Action 3: Optimize database (vacuum if needed)
        try:
            conn = get_connection()
            
            # Check if vacuum is needed (fragmentation)
            cursor = conn.execute("PRAGMA page_count;")
            page_count = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA freelist_count;")
            freelist = cursor.fetchone()[0]
            
            fragmentation = (freelist / page_count * 100) if page_count > 0 else 0
            
            if fragmentation > 20:  # More than 20% fragmented
                if verbose:
                    print(f"⚠️  Database fragmentation: {fragmentation:.1f}%")
                    print("   Running VACUUM (this may take a while)...")
                
                conn.execute("VACUUM;")
                report["actions"].append(f"VACUUM completed (fragmentation was {fragmentation:.1f}%)")
                
                if verbose:
                    print("✅ VACUUM completed")
            else:
                if verbose:
                    print(f"✅ Fragmentation OK: {fragmentation:.1f}%")
            
            conn.close()
            
        except Exception as e:
            report["actions"].append(f"Optimization failed: {str(e)}")
            if verbose:
                print(f"⚠️  Optimization failed: {str(e)}")
        
        # Action 4: Clean old cache entries (optional)
        try:
            conn = get_connection()
            
            cursor = conn.execute("SELECT COUNT(*) FROM ai_cache")
            cache_count = cursor.fetchone()[0]
            
            if cache_count > 5000:
                # Delete oldest 20% of cache
                delete_count = int(cache_count * 0.2)
                conn.execute(f"""
                    DELETE FROM ai_cache 
                    WHERE id IN (
                        SELECT id FROM ai_cache 
                        ORDER BY created_at ASC 
                        LIMIT {delete_count}
                    )
                """)
                report["actions"].append(f"Pruned {delete_count} old cache entries")
                if verbose:
                    print(f"✅ Pruned {delete_count} old cache entries")
            
            conn.close()
            
        except Exception as e:
            report["actions"].append(f"Cache cleanup failed: {str(e)}")
            if verbose:
                print(f"⚠️  Cache cleanup failed: {str(e)}")
        
        # Log healing actions
        log_event("db_monitor", "info", "Database self-healing completed",
                 {"actions": report["actions"], "success": report["success"]})
        
        if verbose:
            print("\n" + "="*60)
            if report["success"]:
                print(f"✅ SELF-HEALING COMPLETE - {len(report['actions'])} actions taken")
            else:
                print(f"⚠️  SELF-HEALING PARTIAL - Some actions failed")
            print("="*60 + "\n")
        
        return report
    
    def get_metrics(self) -> Dict[str, any]:
        """
        Get database performance metrics.
        
        Returns:
            Metrics dictionary
        """
        metrics = {
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = get_connection()
            
            # WAL stats
            cursor = conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            wal_info = cursor.fetchone()
            metrics["wal_busy"] = wal_info[0]
            metrics["wal_log_pages"] = wal_info[1]
            metrics["wal_checkpointed_pages"] = wal_info[2]
            
            # Cache stats
            cursor = conn.execute("PRAGMA cache_size;")
            metrics["cache_size_pages"] = cursor.fetchone()[0]
            
            # Page size
            cursor = conn.execute("PRAGMA page_size;")
            metrics["page_size_bytes"] = cursor.fetchone()[0]
            
            # Database size
            cursor = conn.execute("PRAGMA page_count;")
            page_count = cursor.fetchone()[0]
            metrics["db_size_mb"] = round((page_count * metrics["page_size_bytes"]) / (1024 * 1024), 2)
            
            conn.close()
            
        except Exception as e:
            metrics["error"] = str(e)
        
        return metrics


# Convenience functions
def monitor_database(verbose: bool = True) -> Dict[str, any]:
    """Run database health check."""
    monitor = DatabaseMonitor()
    return monitor.check_health(verbose=verbose)


def heal_database(verbose: bool = True) -> Dict[str, any]:
    """Run database self-healing."""
    monitor = DatabaseMonitor()
    return monitor.self_heal(verbose=verbose)


def get_db_metrics() -> Dict[str, any]:
    """Get database performance metrics."""
    monitor = DatabaseMonitor()
    return monitor.get_metrics()


if __name__ == "__main__":
    # Run health check and self-healing when executed directly
    print("🔧 Database Monitor & Self-Healing Utility")
    print("="*60)
    
    monitor = DatabaseMonitor()
    
    # Health check
    health = monitor.check_health(verbose=True)
    
    # Self-healing if issues detected
    if not health["healthy"] or len(health["warnings"]) > 0:
        print("\n🩺 Issues detected, attempting self-healing...")
        time.sleep(1)
        heal_report = monitor.self_heal(verbose=True)
    
    # Show metrics
    print("\n📊 DATABASE METRICS")
    print("="*60)
    metrics = monitor.get_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    print("="*60)

