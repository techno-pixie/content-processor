import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const submitContent = async (content) => {
  const response = await apiClient.post('/submissions/', { content });
  return response.data;
};

export const getSubmissionStatus = async (submissionId) => {
  const response = await apiClient.get(`/submissions/${submissionId}`);
  return response.data;
};

export const listSubmissions = async () => {
  const response = await apiClient.get('/submissions/');
  return response.data;
};
