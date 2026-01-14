import React from 'react';
import { useState, useEffect } from 'react';
import { submitContent, getSubmissionStatus, listSubmissions } from './api/submissionAPI';
import SubmissionForm from './submission-form/SubmissionForm';
import SubmissionStatus from './submission-status/SubmissionStatus';
import './SubmissionPage.scss';

function SubmissionPage() {
  const [allSubmissions, setAllSubmissions] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const ITEMS_PER_PAGE = 2;
  const totalPages = Math.ceil(allSubmissions.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const currentSubmissions = allSubmissions.slice(startIndex, endIndex);

  // Load all submissions on mount and when new submission is added
  useEffect(() => {
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const submissions = await listSubmissions();
      setAllSubmissions(submissions);
      setCurrentPage(1); // Reset to first page
    } catch (error) {
      console.error('Error loading submissions:', error);
      setError('Failed to load submissions');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (content) => {
    try {
      const newSubmission = await submitContent(content);
      
      // Add to the beginning of the list
      setAllSubmissions([newSubmission, ...allSubmissions]);
      setCurrentPage(1); // Go back to first page to see new submission
      
      // Poll status for the new submission
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
        
        setAllSubmissions(prevSubmissions =>
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

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleRefresh = async () => {
    await loadSubmissions();
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
          <div className="results-header">
            <h2>Submissions History</h2>
            <button 
              className="refresh-btn" 
              onClick={handleRefresh}
              disabled={isLoading}
            >
              {isLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {error ? (
            <div className="error-message">
              {error}
            </div>
          ):<>{isLoading && allSubmissions.length === 0 ? (
            <p className="loading-state">Loading submissions...</p>
          ) : allSubmissions.length === 0 ? (
            <p className="empty-state">No submissions yet. Submit content to get started!</p>
          ) : (
            <>
              <div className="submissions-list">
                {currentSubmissions.map(submission => (
                  <SubmissionStatus key={submission.id} submission={submission} />
                ))}
              </div>

              {totalPages > 1 && (
                <div className="pagination">
                  <button 
                    className="pagination-btn"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    ← Previous
                  </button>

                  <div className="pagination-info">
                    Page <span className="current-page">{currentPage}</span> of <span className="total-pages">{totalPages}</span>
                    <span className="total-count"> ({allSubmissions.length} total)</span>
                  </div>

                  <button 
                    className="pagination-btn"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
          </>}
        </section>
      </main>
    </div>
  );
}

export default SubmissionPage;
