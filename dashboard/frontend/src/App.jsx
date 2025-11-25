import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import TicketDetail from './TicketDetail';
import './App.css';

const API_BASE = 'http://localhost:8000';

// Status color mapping
const STATUS_COLORS = {
  'Pending': 'bg-purple-100 text-purple-800',
  'Agent Planning': 'bg-blue-100 text-blue-800',
  'Agent at Work': 'bg-yellow-100 text-yellow-800',
  'Requesting User Input': 'bg-red-100 text-red-800',
  'Done': 'bg-green-100 text-green-800',
  'Error': 'bg-gray-100 text-gray-800',
};

const STATUS_ORDER = ['Pending', 'Agent Planning', 'Agent at Work', 'Requesting User Input', 'Done'];

function TicketCard({ ticket, onStatusChange }) {
  const timeAgo = (date) => {
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-3 border-l-4 border-blue-500 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-800">{ticket.name}</h3>
        <span className={`px-2 py-1 rounded text-xs font-medium ${ticket.is_active ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'}`}>
          {ticket.is_active ? '● LIVE' : '○ Inactive'}
        </span>
      </div>

      <div className="text-sm text-gray-600 space-y-1">
        <p>Turn: {ticket.turn_count}</p>
        <p>Session: <code className="text-xs bg-gray-100 px-1 rounded">{ticket.session_id.slice(0, 8)}...</code></p>
        <p className="text-gray-400">{timeAgo(ticket.last_updated)}</p>
      </div>

      <div className="mt-3 flex gap-2">
        <Link
          to={`/tickets/${ticket.id}`}
          className="text-xs text-blue-600 hover:underline"
        >
          Open Ticket →
        </Link>
      </div>
    </div>
  );
}

function KanbanBoard({ tickets, onStatusChange }) {
  const columns = STATUS_ORDER.map(status => ({
    status,
    tickets: tickets.filter(t => t.status === status)
  }));

  return (
    <div className="grid grid-cols-4 gap-4">
      {columns.map(({ status, tickets }) => (
        <div key={status} className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-700">{status}</h2>
            <span className="bg-gray-200 text-gray-700 rounded-full px-2 py-1 text-xs">
              {tickets.length}
            </span>
          </div>

          <div className="space-y-3">
            {tickets.map(ticket => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                onStatusChange={onStatusChange}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function Stats({ stats }) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm text-gray-600">Total Tickets</div>
        <div className="text-3xl font-bold text-gray-800">{stats.total}</div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm text-gray-600">Active Loops</div>
        <div className="text-3xl font-bold text-green-600">{stats.active_loops}</div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm text-gray-600">In Progress</div>
        <div className="text-3xl font-bold text-yellow-600">
          {(stats.by_status?.['Agent at Work'] || 0) + (stats.by_status?.['Agent Planning'] || 0)}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm text-gray-600">Waiting</div>
        <div className="text-3xl font-bold text-red-600">
          {stats.by_status?.['Requesting User Input'] || 0}
        </div>
      </div>
    </div>
  );
}

function Home() {
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_status: {}, active_loops: 0 });
  const [loading, setLoading] = useState(true);

  const fetchTickets = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tickets`);
      const data = await response.json();
      setTickets(data);
    } catch (error) {
      console.error('Error fetching tickets:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchTickets(), fetchStats()]);
      setLoading(false);
    };

    loadData();

    // Poll every 3 seconds
    const interval = setInterval(() => {
      fetchTickets();
      fetchStats();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleStatusChange = async (ticketId, newStatus) => {
    try {
      await fetch(`${API_BASE}/api/tickets/${ticketId}/status?status=${newStatus}`, {
        method: 'POST',
      });
      fetchTickets();
      fetchStats();
    } catch (error) {
      console.error('Error updating status:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Ralph Wiggum Dashboard
          </h1>
          <p className="text-gray-600">
            Real-time monitoring of autonomous coding agents
          </p>
        </header>

        <Stats stats={stats} />
        <KanbanBoard tickets={tickets} onStatusChange={handleStatusChange} />
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
