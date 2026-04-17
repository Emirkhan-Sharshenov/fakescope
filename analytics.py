"""
Analytics & Feedback System with PostgreSQL support for Render
Falls back to local JSONL if DB not available
"""
import json
import os
from datetime import datetime
from pathlib import Path
import hashlib

class AnalyticsManager:
    def __init__(self, db_url=None, data_dir='data'):
        """
        Initialize analytics manager.
        - If db_url is provided (PostgreSQL), use it
        - Otherwise fall back to local JSONL files
        """
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.use_db = False
        self.data_dir = Path(data_dir)
        
        # Try to initialize PostgreSQL
        if self.db_url:
            self._init_postgres()
        else:
            # Fall back to local JSONL
            self.data_dir.mkdir(exist_ok=True)
            self.visitors_file = self.data_dir / 'visitors.jsonl'
            self.feedback_file = self.data_dir / 'feedback.jsonl'
    
    def _init_postgres(self):
        """Initialize PostgreSQL connection and tables"""
        try:
            import psycopg2
            from psycopg2.pool import SimpleConnectionPool
            
            # Parse DATABASE_URL
            # Format: postgresql://user:password@host:port/database
            self.conn_pool = SimpleConnectionPool(1, 5, self.db_url)
            self.use_db = True
            self._create_pg_tables()
            print("✅ PostgreSQL connected for analytics")
        except ImportError:
            print("⚠️ psycopg2 not installed. Install: pip install psycopg2-binary")
            self.use_db = False
            self.data_dir.mkdir(exist_ok=True)
            self.visitors_file = self.data_dir / 'visitors.jsonl'
            self.feedback_file = self.data_dir / 'feedback.jsonl'
        except Exception as e:
            print(f"⚠️ PostgreSQL failed: {e}. Using local JSONL storage")
            self.use_db = False
            self.data_dir.mkdir(exist_ok=True)
            self.visitors_file = self.data_dir / 'visitors.jsonl'
            self.feedback_file = self.data_dir / 'feedback.jsonl'
    
    def _create_pg_tables(self):
        """Create PostgreSQL tables if they don't exist"""
        if not self.use_db:
            return
        
        try:
            conn = self.conn_pool.getconn()
            cur = conn.cursor()
            
            # Visitors table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visitors (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_hash VARCHAR(16),
                    user_agent VARCHAR(100),
                    language VARCHAR(5)
                )
            """)
            
            # Feedback table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_hash VARCHAR(16),
                    analysis_id VARCHAR(100),
                    rating VARCHAR(5),
                    comment TEXT,
                    language VARCHAR(5)
                )
            """)
            
            conn.commit()
            cur.close()
            self.conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error creating tables: {e}")
    
    def track_visitor(self, ip, user_agent, lang='ru'):
        """Log a visitor"""
        try:
            visitor_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'ip_hash': hashlib.sha256(ip.encode()).hexdigest()[:16],
                'user_agent': user_agent[:100],
                'language': lang
            }
            
            if self.use_db:
                self._track_visitor_pg(visitor_data)
            else:
                self._track_visitor_local(visitor_data)
        except Exception as e:
            print(f"Error tracking visitor: {e}")
    
    def _track_visitor_pg(self, data):
        """Store visitor in PostgreSQL"""
        try:
            conn = self.conn_pool.getconn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO visitors (ip_hash, user_agent, language) VALUES (%s, %s, %s)",
                (data['ip_hash'], data['user_agent'], data['language'])
            )
            conn.commit()
            cur.close()
            self.conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error inserting visitor: {e}")
    
    def _track_visitor_local(self, data):
        """Store visitor in local JSONL"""
        try:
            with open(self.visitors_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Error writing visitor: {e}")
    
    def save_feedback(self, ip, analysis_id, rating, comment='', lang='ru'):
        """Save user feedback"""
        try:
            feedback_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'ip_hash': hashlib.sha256(ip.encode()).hexdigest()[:16],
                'analysis_id': analysis_id,
                'rating': rating,
                'comment': comment[:500],
                'language': lang
            }
            
            if self.use_db:
                return self._save_feedback_pg(feedback_data)
            else:
                return self._save_feedback_local(feedback_data)
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
    
    def _save_feedback_pg(self, data):
        """Store feedback in PostgreSQL"""
        try:
            conn = self.conn_pool.getconn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO feedback (ip_hash, analysis_id, rating, comment, language) VALUES (%s, %s, %s, %s, %s)",
                (data['ip_hash'], data['analysis_id'], data['rating'], data['comment'], data['language'])
            )
            conn.commit()
            cur.close()
            self.conn_pool.putconn(conn)
            return True
        except Exception as e:
            print(f"Error inserting feedback: {e}")
            return False
    
    def _save_feedback_local(self, data):
        """Store feedback in local JSONL"""
        try:
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            print(f"Error writing feedback: {e}")
            return False
    
    def get_stats(self):
        """Get analytics statistics"""
        if self.use_db:
            return self._get_stats_pg()
        else:
            return self._get_stats_local()
    
    def _get_stats_pg(self):
        """Get stats from PostgreSQL"""
        stats = {
            'total_visitors': 0,
            'total_feedback': 0,
            'thumbs_up': 0,
            'thumbs_down': 0,
            'languages': {},
            'recent_feedback': []
        }
        
        try:
            conn = self.conn_pool.getconn()
            cur = conn.cursor()
            
            # Count visitors
            cur.execute("SELECT COUNT(*) FROM visitors")
            stats['total_visitors'] = cur.fetchone()[0]
            
            # Count feedback
            cur.execute("SELECT COUNT(*) FROM feedback")
            stats['total_feedback'] = cur.fetchone()[0]
            
            # Count thumbs
            cur.execute("SELECT COUNT(*) FROM feedback WHERE rating = 'up'")
            stats['thumbs_up'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM feedback WHERE rating = 'down'")
            stats['thumbs_down'] = cur.fetchone()[0]
            
            # Languages
            cur.execute("SELECT language, COUNT(*) FROM feedback GROUP BY language")
            for lang, count in cur.fetchall():
                stats['languages'][lang] = count
            
            # Recent feedback
            cur.execute(
                "SELECT timestamp, rating, comment, language FROM feedback WHERE comment != '' ORDER BY timestamp DESC LIMIT 50"
            )
            for row in cur.fetchall():
                stats['recent_feedback'].append({
                    'timestamp': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    'rating': row[1],
                    'comment': row[2],
                    'language': row[3]
                })
            
            cur.close()
            self.conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error getting stats from DB: {e}")
        
        return stats
    
    def _get_stats_local(self):
        """Get stats from local JSONL"""
        stats = {
            'total_visitors': 0,
            'total_feedback': 0,
            'thumbs_up': 0,
            'thumbs_down': 0,
            'languages': {},
            'recent_feedback': []
        }
        
        try:
            # Count visitors
            if self.visitors_file.exists():
                stats['total_visitors'] = sum(1 for _ in open(self.visitors_file))
            
            # Count feedback
            if self.feedback_file.exists():
                with open(self.feedback_file) as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            stats['total_feedback'] += 1
                            if data['rating'] == 'up':
                                stats['thumbs_up'] += 1
                            else:
                                stats['thumbs_down'] += 1
                            
                            lang = data.get('language', 'unknown')
                            stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
                            
                            if len(stats['recent_feedback']) < 50:
                                stats['recent_feedback'].append({
                                    'timestamp': data['timestamp'],
                                    'rating': data['rating'],
                                    'comment': data.get('comment', ''),
                                    'language': lang
                                })
                        except:
                            pass
        except Exception as e:
            print(f"Error getting stats: {e}")
        
        return stats
    
    def get_approval_rate(self):
        """Calculate approval rate"""
        stats = self.get_stats()
        total = stats['total_feedback']
        if total == 0:
            return None
        return round((stats['thumbs_up'] / total) * 100, 1)
