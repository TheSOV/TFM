/**
 * Blackboard Page Component
 * Displays real-time updates from the DevopsFlow process
 */

window.BlackboardPage = {
  name: 'BlackboardPage',
  components: {
    'user-request-display': UserRequestDisplay,
    'plans-display': PlansDisplay,
    'manifests-tree': ManifestsTree,
    'images-list': ImagesList,
    'issues-list': IssuesList,
    'records-list': RecordsList,
    'general-info-display': GeneralInfoDisplay,
    'events-panel': window.components?.EventsPanel || { template: '<div></div>' }
  },
  
    template: `
    <q-page padding class="column no-wrap" style="max-width: 100vw; overflow-x: hidden; min-height: calc(100vh - 50px);">
      <style>
        .card-container, .card-container > .q-card, .card-container > .q-card > .q-card__section:not(.bg-primary) {
          display: flex;
          flex-direction: column;
          flex-grow: 1;
          min-height: 0; /* Prevents flex items from overflowing */
        }
        .main-content-grid, .main-content-grid > .row {
          flex-grow: 1;
        }
        .main-content-grid .column-wrapper {
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        .main-content-grid .column-wrapper > * { /* Targets the component tag, e.g., <issues-list> */
          flex-grow: 1;
          display: flex;
          flex-direction: column;
        }
        .main-content-grid .column-wrapper > * > .q-card { /* Targets the root q-card of the component */
          flex-grow: 1;
          display: flex;
          flex-direction: column;
        }
        .scrollable-card-section {
          flex-grow: 1;
          overflow-y: auto;
        }
      </style>
      <div class="card-container">
        <q-card class="shadow-3">
          <q-card-section class="bg-primary text-white">
            <div class="row items-center">
              <!-- Header Content -->
              <q-btn flat round icon="history" @click="$root.leftDrawerOpen = !$root.leftDrawerOpen" color="white" class="q-mr-sm">
                <q-tooltip>Toggle Events</q-tooltip>
              </q-btn>
              <div class="text-h5 text-weight-bold">
                <q-icon name="dashboard" class="q-mr-sm" />
                Blackboard
              </div>
              <div class="q-ml-md row items-center q-gutter-x-md">
                <div class="row items-center text-white">
                  <q-icon name="sync" class="q-mr-xs" />
                  <span class="text-weight-medium q-mr-xs">Phase:</span>{{ phase || 'N/A' }}
                </div>
                <div class="row items-center text-white">
                  <q-icon name="loop" class="q-mr-xs" />
                  <span class="text-weight-medium q-mr-xs">Iteration:</span>{{ iterations }}
                </div>
              </div>
              <q-space />
              <q-badge v-if="lastUpdated" color="blue-grey-7" text-color="white" class="q-mr-sm">
                <q-icon name="schedule" size="xs" class="q-mr-xs" />
                {{ lastUpdated }}
              </q-badge>
              <q-btn-group flat>
                <q-btn flat round :icon="autoRefresh ? 'pause' : 'play_arrow'" @click="toggleAutoRefresh" color="white" :disable="isRefreshing">
                  <q-tooltip>{{ autoRefresh ? 'Pause auto-refresh' : 'Resume auto-refresh' }}</q-tooltip>
                </q-btn>
                <q-btn flat round icon="refresh" @click="fetchBlackboard" :loading="isRefreshing" color="white">
                  <q-tooltip>Refresh now</q-tooltip>
                </q-btn>
                <q-btn flat round icon="article" @click="$root.rightDrawerOpen = !$root.rightDrawerOpen" color="white">
                  <q-tooltip>Toggle Records</q-tooltip>
                </q-btn>
              </q-btn-group>
            </div>
          </q-card-section>
          
          <q-separator />
          
          <q-card-section class="main-content-grid">
            <div v-if="!blackboard" class="text-center q-pa-xl text-grey-7">
              <q-icon name="hourglass_empty" size="3rem" class="q-mb-md" />
              <div class="text-h6">Blackboard is Empty</div>
              <div>Content will appear here once a DevopsFlow is initiated.</div>
            </div>
            <div v-else class="row q-col-gutter-md full-height">
              <!-- Left Column -->
              <div class="col-xs-12 col-md-6">
                <div class="column-wrapper q-gutter-y-md">
                  <user-request-display :request="userRequest" :basic-plan="basicPlanContent" :advanced-plan="advancedPlanContent"></user-request-display>
                  <general-info-display :general-info="generalInfo"></general-info-display>
                  <images-list :images="images"></images-list>
                  <manifests-tree :manifests-data="manifests"></manifests-tree>
                </div>
              </div>

              <!-- Right Column -->
              <div class="col-xs-12 col-md-6">
                <div class="column-wrapper q-gutter-y-md">
                  <issues-list :issues="issues"></issues-list>
                </div>
              </div>
            </div>
          </q-card-section>
          
          <q-separator />
          
          <q-card-actions align="right" class="q-pa-md">
            <q-btn label="Back to Home" to="/" color="primary" flat icon="arrow_back" no-caps padding="8px 16px" />
            <q-btn label="Copy to Clipboard" color="secondary" outline icon="content_copy" @click="copyToClipboard" :disable="!formattedBlackboard" no-caps padding="8px 16px" />
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
    </q-page>
  `,

  data() {
    return {
      blackboard: null,
      lastUpdated: '',
      isRefreshing: false,
      autoRefresh: true,
      refreshInterval: null,
      phase: '',
      projectName: '',
      iterations: 0,
    };
  },

  computed: {
    generalInfo() {
      return this.blackboard && this.blackboard.general_info ? this.blackboard.general_info : { namespaces: [] };
    },
    
    events() {
      // The backend sends a nested structure: { events: { events: [...] } }
      // We need to extract the inner array and pass it to the EventsPanel component.
      if (this.blackboard && this.blackboard.events && Array.isArray(this.blackboard.events.events)) {
        return this.blackboard.events.events;
      }
      return [];
    },
    
    userRequest() {
      console.log('[Computed UserRequest] this.blackboard:', JSON.parse(JSON.stringify(this.blackboard)));
      const req = this.blackboard?.project?.user_request;
      console.log('[Computed UserRequest] req value:', req);
      // If req is an empty string, display it as such.
      // If req is null or undefined, then use the default message.
      if (req === '') return ''; 
      return req || 'User request not available.';
    },
    basicPlanContent() {
      return this.blackboard?.project?.basic_plan || '';
    },
    advancedPlanContent() {
      return this.blackboard?.project?.advanced_plan || '';
    },
    manifests() {
      return this.blackboard?.manifests || {};
    },
    images() {
      return this.blackboard?.images || [];
    },
    issues() {
      return this.blackboard?.issues || [];
    },
    records() {
      return this.blackboard?.records || [];
    },
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
        console.log('[FetchBlackboard] API response.data:', JSON.parse(JSON.stringify(response.data)));
        this.blackboard = response.data.blackboard; // Assuming the actual blackboard data is in response.data.blackboard
        console.log('[FetchBlackboard] this.blackboard after assignment:', JSON.parse(JSON.stringify(this.blackboard)));
        if (this.blackboard && this.blackboard.project) {
          console.log('[FetchBlackboard] this.blackboard.project.user_request:', this.blackboard.project.user_request);
        } else {
          console.log('[FetchBlackboard] this.blackboard or this.blackboard.project is not set.');
        }
        this.iterations = this.blackboard?.iterations ?? 0;
        this.lastUpdated = new Date().toLocaleTimeString();
        this.phase = this.blackboard?.phase || 'Phase not available';
        this.projectName = this.blackboard?.project?.project_name || 'N/A';
        this.$emit('update-drawers', this.blackboard);
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
