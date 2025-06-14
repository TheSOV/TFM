/**
 * Blackboard Page Component
 * Displays real-time updates from the DevopsFlow process
 */

export default {
  name: 'BlackboardPage',
  
  template: `
    <div class="page-container">
      <div class="card-container">
        <q-card class="shadow-3">
          <q-card-section class="bg-grey-2">
            <div class="row items-center">
              <div class="text-h5 text-weight-bold">
                <q-icon name="description" color="primary" class="q-mr-sm" />
                Blackboard
              </div>
              <q-space />
              <q-badge v-if="lastUpdated" color="grey-5" text-color="white" class="q-mr-sm">
                <q-icon name="schedule" size="xs" class="q-mr-xs" />
                {{ lastUpdated }}
              </q-badge>
              <q-btn-group flat>
                <q-btn 
                  flat 
                  round 
                  :icon="autoRefresh ? 'pause' : 'play_arrow'" 
                  @click="toggleAutoRefresh"
                  :color="autoRefresh ? 'primary' : 'grey-7'"
                  :disable="isRefreshing"
                >
                  <q-tooltip>{{ autoRefresh ? 'Pause auto-refresh' : 'Resume auto-refresh' }}</q-tooltip>
                </q-btn>
                <q-btn 
                  flat 
                  round 
                  icon="refresh" 
                  @click="fetchBlackboard" 
                  :loading="isRefreshing"
                  color="grey-7"
                >
                  <q-tooltip>Refresh now</q-tooltip>
                </q-btn>
              </q-btn-group>
            </div>
          </q-card-section>
          
          <q-separator />
          
          <q-card-section class="q-pa-none">
            <pre class="blackboard-content">
              <template v-if="formattedBlackboard">
                {{ formattedBlackboard }}
              </template>
              <div v-else class="text-center q-pa-lg text-grey-7">
                <q-icon name="info" size="2rem" class="q-mb-sm" />
                <div>No blackboard content available</div>
                <div class="text-caption q-mt-sm">Submit a task from the Home page to see updates here</div>
              </div>
            </pre>
          </q-card-section>
          
          <q-separator />
          
          <q-card-actions align="right" class="q-pa-md">
            <q-btn 
              label="Back to Home" 
              to="/" 
              color="primary" 
              flat 
              icon="arrow_back"
              no-caps
              padding="8px 16px"
            />
            <q-btn 
              label="Copy to Clipboard" 
              color="secondary" 
              outline 
              icon="content_copy"
              @click="copyToClipboard"
              :disable="!formattedBlackboard"
              no-caps
              padding="8px 16px"
            />
          </q-card-actions>
        </q-card>
        
        <div class="q-mt-md text-center text-grey-7 text-caption">
          <div class="q-mb-xs">
            <q-icon name="info" size="xs" class="q-mr-xs" />
            The blackboard shows real-time updates from the DevopsFlow process
          </div>
          <div v-if="autoRefresh" class="text-amber-8">
            <q-icon name="sync" size="xs" class="q-mr-xs" />
            Auto-refresh is enabled (every 5 seconds)
          </div>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      blackboard: null,
      lastUpdated: '',
      isRefreshing: false,
      autoRefresh: true,
      refreshInterval: null
    };
  },

  computed: {
    formattedBlackboard() {
      if (!this.blackboard) return '';
      
      try {
        if (typeof this.blackboard === 'string') {
          try {
            const parsed = JSON.parse(this.blackboard);
            return this.formatBlackboard(parsed);
          } catch (e) {
            return this.blackboard; // Return as-is if not valid JSON
          }
        }
        return this.formatBlackboard(this.blackboard);
      } catch (e) {
        console.error('Error formatting blackboard:', e);
        return 'Error displaying blackboard content';
      }
    }
  },

  methods: {
    formatBlackboard(data) {
      if (!data) return '';
      
      if (data.content) {
        return data.content;
      } else if (data.message) {
        return data.message;
      } else if (typeof data === 'object') {
        return JSON.stringify(data, null, 2);
      }
      
      return String(data);
    },

    async fetchBlackboard() {
      if (this.isRefreshing) return;
      
      this.isRefreshing = true;
      
      try {
        const response = await this.$api.getBlackboard();
        this.blackboard = response.data;
        this.lastUpdated = new Date().toLocaleTimeString();
      } catch (error) {
        console.error('Error fetching blackboard:', error);
        this.$q.notify({
          type: 'negative',
          message: 'Failed to fetch blackboard',
          caption: error.response?.data?.message || error.message,
          position: 'top',
          timeout: 3000,
          actions: [{ label: 'Retry', color: 'yellow', handler: this.fetchBlackboard }]
        });
      } finally {
        this.isRefreshing = false;
      }
    },

    toggleAutoRefresh() {
      this.autoRefresh = !this.autoRefresh;
      
      if (this.autoRefresh) {
        this.setupAutoRefresh();
        this.fetchBlackboard();
      } else {
        this.clearAutoRefresh();
      }
    },

    setupAutoRefresh() {
      this.clearAutoRefresh();
      this.refreshInterval = setInterval(() => {
        if (this.autoRefresh) {
          this.fetchBlackboard();
        }
      }, 5000);
    },

    clearAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
        this.refreshInterval = null;
      }
    },

    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.formattedBlackboard);
        this.$q.notify({
          type: 'positive',
          message: 'Copied to clipboard!',
          position: 'top',
          timeout: 2000
        });
      } catch (err) {
        console.error('Failed to copy:', err);
        this.$q.notify({
          type: 'negative',
          message: 'Failed to copy to clipboard',
          position: 'top'
        });
      }
    }
  },

  created() {
    this.fetchBlackboard();
    if (this.autoRefresh) {
      this.setupAutoRefresh();
    }
  },

  beforeUnmount() {
    this.clearAutoRefresh();
  }
};

// This module provides the BlackboardPage component for the DevopsFlow application.
// It displays real-time updates from the DevopsFlow process and allows users to monitor progress.
// The component includes auto-refresh functionality and clipboard support.
