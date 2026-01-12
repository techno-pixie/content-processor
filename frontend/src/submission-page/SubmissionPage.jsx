import { useState, useEffect } from 'react';
import { submitContent, getSubmissionStatus } from './api/submissionAPI';
import SubmissionForm from './submission-form/SubmissionForm';
import SubmissionStatus from './submission-status/SubmissionStatus';
import './SubmissionPage.scss';
function SubmissionPage() {
  const [submissions, setSubmissions] = useState([]);

  const handleSubmit = async (content) => {
    try {
      const newSubmission = await submitContent(content);
      setSubmissions([newSubmission, ...submissions]);
      
      pollStatus(newSubmission.id);
    } catch (error) {
      console.error('Error submitting content:', error);
      alert('Error submitting content. Please try again.');
    }
  };

  const pollStatus = (submissionId) => {
    const pollInterval = setInterval(async () => {
      try {
        const updatedSubmission = await getSubmissionStatus(submissionId);
        
        setSubmissions(prevSubmissions =>
          prevSubmissions.map(sub =>
            sub.id === submissionId ? updatedSubmission : sub
          )
        );

        if (updatedSubmission.status === 'PASSED' || updatedSubmission.status === 'FAILED') {
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Error fetching submission status:', error);
        clearInterval(pollInterval);
      }
    }, 1000); 

    setTimeout(() => clearInterval(pollInterval), 15000);
  };

  return (
    <div className="container">
      <header className="header">
        <h1>Content Processor</h1>
        <p>Submit content and track its processing status in real-time</p>
      </header>

      <main className="main">
        <section className="form-section">
          <SubmissionForm onSubmit={handleSubmit} />
        </section>

        <section className="results-section">
          <h2>Submissions</h2>
          {submissions.length === 0 ? (
            <p className="empty-state">No submissions yet. Submit content to get started!</p>
          ) : (
            <div className="submissions-list">
              {submissions.map(submission => (
                <SubmissionStatus key={submission.id} submission={submission} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default SubmissionPage;
