import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const AdminSidebar = ({ activeTab }) => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();

  const sidebarNavItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', path: '/admin', isPlaceholder: false },
    { id: 'users', label: 'Users', icon: '👥', path: '/admin/users', isPlaceholder: false },
    { id: 'projects', label: 'Projects', icon: '📁', path: '/admin/projects', isPlaceholder: false },
    { id: 'papers', label: 'Papers', icon: '📄', path: '/admin/papers', isPlaceholder: false },
    { id: 'activity', label: 'Activity', icon: '⚡', path: null, isPlaceholder: true, tag: 'Coming Soon' },
  ];

  return (
    <aside className="admin-sidebar glass-panel">
      <div className="admin-sidebar-section">
        <span className="admin-sidebar-heading">Admin Console</span>
        <nav className="admin-sidebar-nav">
          {sidebarNavItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`admin-nav-item ${activeTab === item.id ? 'active' : ''} ${item.isPlaceholder ? 'placeholder' : ''}`}
              onClick={() => {
                if (!item.isPlaceholder && item.path) {
                  navigate(item.path);
                }
              }}
              disabled={item.isPlaceholder}
              title={item.isPlaceholder ? `${item.label} management is planned for future phases` : item.label}
            >
              <span className="nav-item-icon">{item.icon}</span>
              <span className="nav-item-label">{item.label}</span>
              {item.tag && <span className="nav-item-tag">{item.tag}</span>}
            </button>
          ))}
        </nav>
      </div>

      <div className="admin-user-card">
        <div className="admin-user-avatar">
          {user?.username ? user.username.charAt(0).toUpperCase() : 'A'}
        </div>
        <div className="admin-user-details">
          <span className="admin-user-name">{user?.username}</span>
          <span className="admin-user-role">
            {user?.is_superuser ? 'Super Administrator' : 'Platform Staff'}
          </span>
        </div>
      </div>
    </aside>
  );
};

export default AdminSidebar;
