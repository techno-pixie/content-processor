import React from 'react';
import './SubmissionStatus.scss';
import moment from 'moment-timezone';

function SubmissionStatus({ submission }) {
  const getStatusClass = (status) => {
    switch (status) {
      case 'PENDING':
      case 'PROCESSING':
        return 'status-pending';
      case 'PASSED':
        return 'status-passed';
      case 'FAILED':
        return 'status-failed';
      default:
        return '';
    }
  };

  const formatDate = (dateString) => {
    const tz = moment.tz.guess();
    const time = moment.utc(dateString).clone().tz(tz).format('YYYY-MM-DD hh:mm:ss a');
    return time;
  };

  return (
    <div className={`submission-card ${getStatusClass(submission.status)}`}>
      <div className="card-header">
        <div className="status-badge">
          <span className="status-text">{submission.status}</span>
        </div>
        <code className="submission-id">{submission.id.substring(0, 8)}...</code>
      </div>
      
      <div className="card-content">
        <div className="content-block">
          <strong>Content:</strong>
          <p>{submission.content}</p>
        </div>
        
        <div className="timestamps">
          <div className="timestamp">
            <span className="label">Submitted:</span>
            <span className="value">{formatDate(submission.created_at)}</span>
          </div>
          {submission.processed_at && (
            <div className="timestamp">
              <span className="label">Processed:</span>
              <span className="value">{formatDate(submission.processed_at)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SubmissionStatus;
