/**
 * API Service
 * Handles all API communication with the backend
 */



const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 10000 // 10 seconds
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle specific error status codes
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error:', {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        config: error.config
      });
      
      // Handle 401 Unauthorized (e.g., token expired)
      if (error.response.status === 401) {
        // Redirect to login or handle token refresh
        console.warn('Authentication required');
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Request setup error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

const apiService = {
  // DevopsFlow endpoints
  initDevopsFlow(prompt) {
    return apiClient.post('/init', { prompt });
  },
  
  getBlackboard() {
    return apiClient.get('/blackboard');
  },
  
  getStatus() {
    return apiClient.get('/status');
  },

  killDevopsFlow() {
    return apiClient.post('/kill');
  },
  
  // Add more API methods as needed
};

window.apiService = apiService;
