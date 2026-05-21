import React from 'react';
import './SyncModal.css';

const SyncModal = ({ message, isError, onClose }) => (
  <div className="sync-overlay">
    <div className="sync-modal">
      {isError ? (
        <div className="sync-icon sync-icon--error">✕</div>
      ) : (
        <div className="sync-spinner" />
      )}
      <p className="sync-title">{isError ? '資料更新失敗' : '正在更新資料'}</p>
      <p className="sync-message">{message}</p>
      {isError && (
        <button className="sync-close-btn" onClick={onClose}>關閉</button>
      )}
    </div>
  </div>
);

export default SyncModal;
