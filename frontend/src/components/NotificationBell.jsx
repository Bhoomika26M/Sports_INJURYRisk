import React, { useState, useEffect, useRef } from 'react';
import { invitationsAPI } from '../services/api';

const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actingId, setActingId] = useState(null);
  const dropdownRef = useRef(null);

  const pending = notifications.filter((n) => n.status === 'pending');

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 30000); // 30s background poll
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadNotifications = async () => {
    try {
      const res = await invitationsAPI.getNotifications();
      setNotifications(res.data || []);
    } catch (err) {
      console.debug('Failed to poll notifications', err);
    }
  };

  const handleRespond = async (invitationId, action) => {
    try {
      setActingId(invitationId);
      await invitationsAPI.respond(invitationId, action);
      await loadNotifications();
    } catch (err) {
      alert(err.response?.data?.detail || `Failed to ${action} invitation`);
    } finally {
      setActingId(null);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-xl hover:bg-[#F1F3FF] text-[#141B2B] transition-colors flex items-center justify-center"
        title="Athlete Access Invitations"
      >
        <span className="text-lg">🔔</span>
        {pending.length > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#BD4006] text-[10px] font-bold text-white shadow-sm animate-pulse">
            {pending.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white shadow-xl border border-gray-100 py-3 z-50">
          <div className="px-4 py-2 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-sm text-[#141B2B]">
                Athlete Invitations
              </span>
              {pending.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-mono font-bold">
                  {pending.length} New
                </span>
              )}
            </div>
            <button
              onClick={loadNotifications}
              className="text-xs text-gray-400 hover:text-gray-600 font-mono"
            >
              Refresh
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-gray-100">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-xs text-gray-500">
                No notifications or invitations yet.
              </div>
            ) : (
              notifications.map((n) => {
                const isPending = n.status === 'pending';
                return (
                  <div key={n.id} className="p-3.5 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-xs font-semibold text-[#141B2B]">
                          Athlete <span className="text-[#BD4006]">{n.athlete_public_id}</span>
                        </p>
                        <p className="text-[11px] text-[#594139] mt-0.5">
                          Invited you to access their movement profile & telemetry as a{' '}
                          <span className="font-semibold text-gray-700">
                            {n.invited_role?.replace(/_/g, ' ')}
                          </span>
                        </p>
                        {n.notes && (
                          <p className="text-[11px] text-gray-400 italic mt-0.5">
                            "{n.notes}"
                          </p>
                        )}
                        <p className="text-[10px] text-gray-400 mt-1 font-mono">
                          {new Date(n.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-semibold ${
                          n.status === 'accepted'
                            ? 'bg-emerald-100 text-emerald-800'
                            : n.status === 'pending'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {n.status}
                      </span>
                    </div>

                    {isPending && (
                      <div className="mt-3 flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleRespond(n.id, 'reject')}
                          disabled={actingId === n.id}
                          className="px-2.5 py-1 text-xs rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors"
                        >
                          Decline
                        </button>
                        <button
                          onClick={() => handleRespond(n.id, 'accept')}
                          disabled={actingId === n.id}
                          className="px-3 py-1 text-xs rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-semibold shadow-sm transition-colors"
                        >
                          {actingId === n.id ? 'Saving...' : 'Accept'}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
