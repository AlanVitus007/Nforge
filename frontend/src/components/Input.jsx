import React from 'react';
import './Input.css';

const Input = ({ label, id, error, ...props }) => {
  return (
    <div className="input-group">
      {label && <label htmlFor={id}>{label}</label>}
      <input id={id} className={`input ${error ? 'input-error' : ''}`} {...props} />
      {error && <span className="error-text">{error}</span>}
    </div>
  );
};

export default Input;
