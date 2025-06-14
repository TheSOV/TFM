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
    'records-list': RecordsList
  },
  
    template: `
<style>
  /* Ensure the main page card and its content section fill height */
  .blackboard-dashboard .card-container {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .blackboard-dashboard .card-container > .q-card { /* Main page card */
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Important for nested flex */
  }
  /* The q-card-section holding the main grid (not the header section) */
  .blackboard-dashboard .card-container > .q-card > .q-card__section:not(.bg-primary) {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding-top: 0; /* Adjust if too much space from header */
    padding-bottom: 0; /* Adjust if too much space at bottom */
  }
  /* The main grid row itself */
  .blackboard-dashboard .card-container > .q-card > .q-card__section:not(.bg-primary) > .row {
    flex-grow: 1;
    min-height: 0;
  }

  /* Make all direct column children of rows (e.g. col-md-8, col-md-4) flex columns */
  .blackboard-dashboard .row > [class*="col-"] {
    display: flex;
    flex-direction: column;
    /* min-height: 0; /* Add if necessary for deep nesting */
  }
  
  /* Make component cards (q-card directly inside a grid column) fill their grid cell and be flex columns */
  .blackboard-dashboard .row > [class*="col-"] > .q-card,
  .blackboard-dashboard .row > [class*="col-"] > * > .q-card { /* Catches components wrapped in an extra div */
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Crucial for flex item to shrink and grow properly */
  }
  
  /* Style for the content section within each component card to make it scrollable */
  /* Apply class="scrollable-card-section" to the q-card-section that should scroll */
  .blackboard-dashboard .q-card .scrollable-card-section {
    flex-grow: 1;
    overflow-y: auto;
    min-height: 0; /* Important for content to not overflow its flex parent */
    /* Add some padding back if removed from parent sections */
    /* padding: 16px; */ 
  }

  /* Specific adjustments for rows within col-md-8 to distribute height */
  .blackboard-dashboard .col-md-8.column > .row {
    flex-grow: 1; /* Make child rows share the space of col-md-8 */
    min-height: 0;
    /* border: 1px dashed green; /* For debugging layout */
  }

  /* Optional: Define basis for rows within col-md-8 if equal distribution isn't desired */
  /* Example: Give Manifests more space relative to others */
  /* .blackboard-dashboard .col-md-8.column > .row:nth-child(1) { flex-basis: 25%; } /* UserRequest/Plans */
  /* .blackboard-dashboard .col-md-8.column > .row:nth-child(2) { flex-basis: 50%; } /* Manifests */
  /* .blackboard-dashboard .col-md-8.column > .row:nth-child(3) { flex-basis: 25%; } /* Images/Issues */

</style>
    <q-page padding class="blackboard-dashboard column no-wrap" style="max-width: 100vw; overflow-x: hidden; min-height: calc(100vh - 50px); /* Adjust 50px based on actual header height if any, or use 100vh if no persistent header */"> <!-- Ensure full width usage -->
      <div class="card-container">
        <q-card class="shadow-3">
          <q-card-section class="bg-primary text-white">
            <div class="row items-center">
              <div class="text-h5 text-weight-bold">
                <q-icon name="dashboard" class="q-mr-sm" />
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
          
          <q-card-section>
            <div v-if="!blackboard" class="text-center q-pa-xl text-grey-7">
              <q-icon name="hourglass_empty" size="3rem" class="q-mb-md" />
              <div class="text-h6">Blackboard is Empty</div>
              <div>Content will appear here once a DevopsFlow is initiated.</div>
            </div>
            <div v-else class="row q-col-gutter-x-lg q-col-gutter-y-md"> <!-- Added x-gutter for horizontal spacing too -->
              <!-- Left Column -->
              <div class="col-xs-12 col-md-8">
                <div class="row q-col-gutter-md">
                  <div class="col-xs-12 col-sm-6">
                    <user-request-display :request="userRequest"></user-request-display>
                  </div>
                  <div class="col-xs-12 col-sm-6">
                    <plans-display :basic-plan="basicPlanContent" :advanced-plan="advancedPlanContent"></plans-display>
                  </div>
                  <div class="col-12 q-mt-md">
                    <manifests-tree :manifests-data="manifests"></manifests-tree>
                  </div>
                  <div class="col-xs-12 col-sm-6 q-mt-md">
                    <images-list :images="images"></images-list>
                  </div>
                  <div class="col-xs-12 col-sm-6 q-mt-md">
                    <issues-list :issues="issues"></issues-list>
                  </div>
                </div>
              </div>

              <!-- Right Column -->
              <div class="col-xs-12 col-md-4 q-mt-md">
                <div class="q-mb-md q-gutter-sm">
                  <q-chip dense icon="sync" :label="phase || 'N/A'" color="primary" text-color="white">
                    <q-tooltip>Current Phase</q-tooltip>
                  </q-chip>
                  <q-chip dense icon="loop" :label="'Iter: ' + iterations" color="secondary" text-color="white">
                    <q-tooltip>Iterations</q-tooltip>
                  </q-chip>
                </div>
                <!-- Making RecordsList take available height -->
                <records-list :records="records" class="fit-height-component"></records-list> 
              </div>
            </div>
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
      refreshInterval: null,
      phase: '',
      projectName: '',
      iterations: 0,
    };
  },

  computed: {
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
        this.lastUpdated = new Date().toLocaleTimeString();
        this.phase = this.blackboard?.phase || 'Phase not available';
        this.projectName = this.blackboard?.project?.project_name || 'N/A';
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
