import { useState } from 'react';
import './SubmissionForm.css';

function SubmissionForm({ onSubmit }) {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e) => {
    setContent(e.target.value);
  };

  const validateContent = (text) => {
    if (!text.trim()) {
      return 'Please enter some content';
    }
    if (text.length < 10) {
      return 'Content must be at least 10 characters long';
    }
    if (!/\d/.test(text)) {
      return 'Content must contain at least one number (0-9)';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // const error = validateContent(content);
    // if (error) {
    //   alert(error);
    //   return;
    // }

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
        <textarea
          id="content"
          value={content}
          onChange={handleChange}
          placeholder="Enter content to be processed..."
          rows="4"
          disabled={isSubmitting}
        />
      </div>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  );
}

export default SubmissionForm;
