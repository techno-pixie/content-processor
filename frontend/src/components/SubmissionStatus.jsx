import './SubmissionStatus.css';

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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'PASSED':
        return '✓';
      case 'FAILED':
        return '✗';
      case 'PROCESSING':
        return '⟳';
      case 'PENDING':
        return '⧗';
      default:
        return '';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className={`submission-card ${getStatusClass(submission.status)}`}>
      <div className="card-header">
        <div className="status-badge">
          <span className="icon">{getStatusIcon(submission.status)}</span>
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
