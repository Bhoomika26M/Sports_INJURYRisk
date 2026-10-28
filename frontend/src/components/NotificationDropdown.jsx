import { useState, useEffect, useRef } from 'react';
import { 
  Bell, 
  AlertTriangle, 
  ShieldAlert, 
  Activity, 
  Heart, 
  CheckCircle, 
  CheckCheck, 
  RefreshCw,
  X,
  ExternalLink
} from 'lucide-react';
import api from '../api/client';

export const NotificationDropdown = () => {
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('all'); // 'all', 'unread', 'critical'
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const dropdownRef = useRef(null);

  const fetchNotifications = async () => {
    try {
      const [sumRes, listRes] = await Promise.all([
        api.get('/notifications/summary?limit=30'),
        api.get('/notifications?limit=30')
      ]);
      setSummary(sumRes.data);
      setNotifications(listRes.data || []);
    } catch (err) {
      console.warn('Could not load notifications:', err);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 20000); // 20s polling
    return () => clearInterval(interval);
  }, []);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const handleMarkAsRead = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      await api.patch(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      if (summary) {
        setSummary({
          ...summary,
          unread_count: Math.max(0, summary.unread_count - 1),
        });
      }
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      setLoading(true);
      await api.post('/notifications/mark-all-read');
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      if (summary) {
        setSummary({
          ...summary,
          unread_count: 0,
          critical_count: 0,
          warning_count: 0,
        });
      }
    } catch (err) {
      console.error('Failed to mark all read:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncAlerts = async () => {
    try {
      setSyncing(true);
      await api.post('/notifications/sync');
      await fetchNotifications();
    } catch (err) {
      console.error('Failed to sync alerts:', err);
    } finally {
      setSyncing(false);
    }
  };

  const filteredNotifications = notifications.filter((n) => {
    if (filter === 'unread') return !n.is_read;
    if (filter === 'critical') return n.severity === 'critical';
    return true;
  });

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'critical':
        return {
          icon: <AlertTriangle size={15} className="text-rose-600" />,
          bg: 'bg-rose-50 border-rose-200 text-rose-700',
          dot: 'bg-rose-500',
          label: 'Critical'
        };
      case 'warning':
        return {
          icon: <ShieldAlert size={15} className="text-amber-600" />,
          bg: 'bg-amber-50 border-amber-200 text-amber-700',
          dot: 'bg-amber-500',
          label: 'Warning'
        };
      default:
        return {
          icon: <CheckCircle size={15} className="text-blue-600" />,
          bg: 'bg-blue-50 border-blue-200 text-blue-700',
          dot: 'bg-blue-500',
          label: 'Info'
        };
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'high_risk_movement':
        return 'High-Risk Movement';
      case 'injury_risk':
        return 'Injury Risk';
      case 'training_load':
        return 'Training Load';
      case 'recovery_reminder':
        return 'Recovery Reminder';
      case 'assessment_completion':
        return 'Assessment Ready';
      default:
        return type.replace('_', ' ');
    }
  };

  const unreadCount = summary?.unread_count || 0;
  const criticalCount = summary?.critical_count || 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => {
          setOpen(!open);
          if (!open) fetchNotifications();
        }}
        className="relative p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition focus:outline-none"
        title="Notifications & Alerts"
        aria-label="Notifications"
      >
        <Bell size={19} />
        {unreadCount > 0 && (
          <span className={`absolute -top-1 -right-1 flex h-4 min-w-4 px-1 items-center justify-center rounded-full text-[10px] font-bold text-white shadow-xs ${
            criticalCount > 0 ? 'bg-rose-600 animate-pulse' : 'bg-blue-600'
          }`}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {open && (
        <div className="absolute right-0 mt-2 w-96 max-w-[calc(100vw-1.5rem)] bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden animate-in fade-in duration-150">
          {/* Header */}
          <div className="px-4 py-3 bg-slate-900 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">Notifications & Alerts</span>
              {unreadCount > 0 && (
                <span className="bg-rose-500/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleSyncAlerts}
                disabled={syncing}
                title="Sync and scan alerts"
                className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
              >
                <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  disabled={loading}
                  className="text-[11px] text-blue-300 hover:text-blue-100 font-medium px-2 py-0.5 rounded hover:bg-slate-800 transition"
                >
                  Mark all read
                </button>
              )}
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex border-b border-slate-100 px-3 py-1.5 bg-slate-50 text-xs gap-1 font-medium">
            <button
              onClick={() => setFilter('all')}
              className={`px-2.5 py-1 rounded-md transition ${
                filter === 'all'
                  ? 'bg-white shadow-xs text-slate-900 font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              All ({notifications.length})
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-2.5 py-1 rounded-md transition ${
                filter === 'unread'
                  ? 'bg-white shadow-xs text-slate-900 font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Unread ({unreadCount})
            </button>
            <button
              onClick={() => setFilter('critical')}
              className={`px-2.5 py-1 rounded-md transition ${
                filter === 'critical'
                  ? 'bg-white shadow-xs text-rose-700 font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Critical ({summary?.critical_count || 0})
            </button>
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
            {filteredNotifications.length === 0 ? (
              <div className="py-10 text-center text-slate-400">
                <CheckCheck size={28} className="mx-auto mb-2 opacity-50 text-slate-400" />
                <p className="text-xs font-medium">No alerts in this category</p>
                <p className="text-[11px] text-slate-400 mt-0.5">All movements within normal screening limits</p>
              </div>
            ) : (
              filteredNotifications.map((notif) => {
                const s = getSeverityBadge(notif.severity);
                return (
                  <div
                    key={notif.id}
                    onClick={() => !notif.is_read && handleMarkAsRead(notif.id)}
                    className={`p-3.5 hover:bg-slate-50 transition cursor-pointer flex gap-3 items-start ${
                      !notif.is_read ? 'bg-blue-50/40' : ''
                    }`}
                  >
                    {/* Severity Icon */}
                    <div className={`p-1.5 rounded-lg border flex-shrink-0 mt-0.5 ${s.bg}`}>
                      {s.icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          {getTypeLabel(notif.notification_type)}
                        </span>
                        {!notif.is_read && (
                          <span className={`w-2 h-2 rounded-full ${s.dot}`} title="Unread" />
                        )}
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900 line-clamp-1">
                        {notif.title}
                      </h4>
                      <p className="text-[11px] text-slate-600 line-clamp-2 mt-0.5 leading-snug">
                        {notif.message}
                      </p>
                      {notif.created_at && (
                        <span className="text-[10px] text-slate-400 mt-1 block">
                          {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          {' · '}
                          {new Date(notif.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Module 11: Real-time Alerting</span>
            <button
              onClick={() => setOpen(false)}
              className="text-slate-600 hover:text-slate-900 font-medium"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
