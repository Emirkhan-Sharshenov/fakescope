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
    
    def get_detailed_metrics(self):
        """Get detailed metrics for dashboard"""
        if self.use_db:
            return self._get_detailed_metrics_pg()
        else:
            return self._get_detailed_metrics_local()
    
    def _get_detailed_metrics_pg(self):
        """Get detailed metrics from PostgreSQL"""
        metrics = {
            'daily_visits': {},
            'hourly_distribution': {},
            'popular_sources': {},
            'avg_analysis_time': 0,
            'feedback_trends': {},
            'language_trends': {},
            'top_user_agents': []
        }
        
        try:
            conn = self.conn_pool.getconn()
            cur = conn.cursor()
            
            # Daily visits (last 30 days)
            cur.execute("""
                SELECT DATE(timestamp), COUNT(*) 
                FROM visitors 
                WHERE timestamp > CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(timestamp) 
                ORDER BY DATE(timestamp)
            """)
            metrics['daily_visits'] = {str(row[0]): row[1] for row in cur.fetchall()}
            
            # Hourly distribution
            cur.execute("""
                SELECT EXTRACT(hour FROM timestamp), COUNT(*) 
                FROM visitors 
                GROUP BY EXTRACT(hour FROM timestamp) 
                ORDER BY EXTRACT(hour FROM timestamp)
            """)
            metrics['hourly_distribution'] = {int(row[0]): row[1] for row in cur.fetchall()}
            
            # Popular sources (from feedback analysis_id, but we don't have source tracking)
            # This would need additional tracking
            
            # Average analysis time (if stored)
            # Feedback trends by day
            cur.execute("""
                SELECT DATE(timestamp), rating, COUNT(*) 
                FROM feedback 
                WHERE timestamp > CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(timestamp), rating 
                ORDER BY DATE(timestamp)
            """)
            feedback_trends = {}
            for row in cur.fetchall():
                date = str(row[0])
                rating = row[1]
                count = row[2]
                if date not in feedback_trends:
                    feedback_trends[date] = {'up': 0, 'down': 0}
                feedback_trends[date][rating] = count
            metrics['feedback_trends'] = feedback_trends
            
            # Language trends
            cur.execute("""
                SELECT DATE(timestamp), language, COUNT(*) 
                FROM visitors 
                WHERE timestamp > CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(timestamp), language 
                ORDER BY DATE(timestamp)
            """)
            lang_trends = {}
            for row in cur.fetchall():
                date = str(row[0])
                lang = row[1]
                count = row[2]
                if date not in lang_trends:
                    lang_trends[date] = {}
                lang_trends[date][lang] = count
            metrics['language_trends'] = lang_trends
            
            # Top user agents
            cur.execute("""
                SELECT user_agent, COUNT(*) 
                FROM visitors 
                GROUP BY user_agent 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """)
            metrics['top_user_agents'] = [{'agent': row[0][:50], 'count': row[1]} for row in cur.fetchall()]
            
            cur.close()
            self.conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error getting detailed metrics: {e}")
        
        return metrics
    
    def _get_detailed_metrics_local(self):
        """Get detailed metrics from local JSONL"""
        from collections import defaultdict
        import datetime as dt
        
        metrics = {
            'daily_visits': defaultdict(int),
            'hourly_distribution': defaultdict(int),
            'popular_sources': defaultdict(int),
            'avg_analysis_time': 0,
            'feedback_trends': defaultdict(lambda: {'up': 0, 'down': 0}),
            'language_trends': defaultdict(dict),
            'top_user_agents': []
        }
        
        try:
            # Read visitors
            if self.visitors_file.exists():
                with open(self.visitors_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            visit = json.loads(line.strip())
                            timestamp = visit.get('timestamp', '')
                            if timestamp:
                                # Parse date
                                try:
                                    date_obj = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    date = date_obj.date().isoformat()
                                    hour = date_obj.hour
                                    lang = visit.get('language', 'unknown')
                                    
                                    metrics['daily_visits'][date] += 1
                                    metrics['hourly_distribution'][hour] += 1
                                    if date not in metrics['language_trends']:
                                        metrics['language_trends'][date] = {}
                                    metrics['language_trends'][date][lang] = metrics['language_trends'][date].get(lang, 0) + 1
                                except:
                                    pass
                        except:
                            pass
            
            # Read feedback
            if self.feedback_file.exists():
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            fb = json.loads(line.strip())
                            timestamp = fb.get('timestamp', '')
                            rating = fb.get('rating', '')
                            if timestamp and rating in ['up', 'down']:
                                try:
                                    date_obj = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    date = date_obj.date().isoformat()
                                    metrics['feedback_trends'][date][rating] += 1
                                except:
                                    pass
                        except:
                            pass
            
            # Convert defaultdict to dict
            metrics['daily_visits'] = dict(metrics['daily_visits'])
            metrics['hourly_distribution'] = dict(metrics['hourly_distribution'])
            metrics['feedback_trends'] = dict(metrics['feedback_trends'])
            metrics['language_trends'] = dict(metrics['language_trends'])
            
            # Top user agents (simplified)
            ua_counts = defaultdict(int)
            if self.visitors_file.exists():
                with open(self.visitors_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            visit = json.loads(line.strip())
                            ua = visit.get('user_agent', '')[:50]
                            ua_counts[ua] += 1
                        except:
                            pass
            metrics['top_user_agents'] = [{'agent': ua, 'count': count} for ua, count in sorted(ua_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
            
        except Exception as e:
            print(f"Error getting detailed metrics: {e}")
        
        return metrics
    
    def get_verification_data(self):
        """Get data for public verification of analytics authenticity"""
        if self.use_db:
            return self._get_verification_pg()
        else:
            return self._get_verification_local()
    
    def _get_verification_pg(self):
        """Get verification data from PostgreSQL"""
        data = {
            'unique_visitors': 0,
            'unique_feedback_givers': 0,
            'user_agent_diversity': 0,
            'recent_visits': [],
            'language_dist': {}
        }
        
        try:
            conn = self.conn_pool.getconn()
            cur = conn.cursor()
            
            # Unique visitors
            cur.execute("SELECT COUNT(DISTINCT ip_hash) FROM visitors")
            data['unique_visitors'] = cur.fetchone()[0]
            
            # Unique feedback givers
            cur.execute("SELECT COUNT(DISTINCT ip_hash) FROM feedback")
            data['unique_feedback_givers'] = cur.fetchone()[0]
            
            # User agent diversity
            cur.execute("SELECT COUNT(DISTINCT user_agent) FROM visitors")
            data['user_agent_diversity'] = cur.fetchone()[0]
            
            # Recent visits (last 20)
            cur.execute(
                "SELECT timestamp, language, LEFT(user_agent, 30) || '...' as ua_short FROM visitors ORDER BY timestamp DESC LIMIT 20"
            )
            data['recent_visits'] = [
                {'timestamp': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]), 
                 'language': row[1], 'user_agent_short': row[2]}
                for row in cur.fetchall()
            ]
            
            # Language distribution
            cur.execute("SELECT language, COUNT(*) FROM visitors GROUP BY language")
            data['language_dist'] = {row[0]: row[1] for row in cur.fetchall()}
            
            cur.close()
            self.conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error getting verification data: {e}")
        
        return data
    
    def _get_verification_local(self):
        """Get verification data from local JSONL"""
        unique_ips = set()
        feedback_ips = set()
        user_agents = set()
        recent_visits = []
        lang_dist = {}
        
        # Read visitors
        if self.visitors_file.exists():
            with open(self.visitors_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        visit = json.loads(line.strip())
                        ip = visit.get('ip_hash', '')
                        ua = visit.get('user_agent', '')
                        unique_ips.add(ip)
                        user_agents.add(ua)
                        lang = visit.get('language', 'unknown')
                        lang_dist[lang] = lang_dist.get(lang, 0) + 1
                        recent_visits.append({
                            'timestamp': visit.get('timestamp', ''),
                            'language': lang,
                            'user_agent_short': ua[:30] + '...' if len(ua) > 30 else ua
                        })
                    except:
                        pass
            recent_visits = recent_visits[-20:]
        
        # Read feedback
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        fb = json.loads(line.strip())
                        feedback_ips.add(fb.get('ip_hash', ''))
                    except:
                        pass
        
        return {
            'unique_visitors': len(unique_ips),
            'unique_feedback_givers': len(feedback_ips),
            'user_agent_diversity': len(user_agents),
            'recent_visits': recent_visits,
            'language_dist': lang_dist
        }
