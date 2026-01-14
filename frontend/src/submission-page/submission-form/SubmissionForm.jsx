import React from 'react';
import { useState } from 'react';
import './SubmissionForm.scss';

function SubmissionForm({ onSubmit }) {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e) => {
    setContent(e.target.value);
  };


  const handleSubmit = async (e) => {
    e.preventDefault();

    setIsSubmitting(true);
    try {
      await onSubmit(content);
      setContent('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="submission-form" onSubmit={handleSubmit}>
      <h2>Submit Content</h2>
      <div className="form-group">
        <label htmlFor="content">Content to Process:</label>
        <input
          id="content"
          type="text"
          value={content}
          onChange={handleChange}
          placeholder="Enter content to be processed (min 10 characters, must contain a digit)..."
        />
      </div>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  );
}

export default SubmissionForm;
