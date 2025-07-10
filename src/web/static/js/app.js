/**
 * Main Application Entry Point
 * Initializes the Vue 3 application with Quasar and Vue Router
 */
const { createApp } = Vue;

// The main Quasar object from the UMD script
const Quasar = window.Quasar;

const app = createApp({
  template: `
    <q-layout view="hHh lpr fff">
      <q-header elevated class="bg-primary text-white">
        <q-toolbar>
          <q-toolbar-title class="text-h5 text-weight-bold">
            <q-icon name="mdi-robot" class="q-mr-sm" />
            DevopsFlow
          </q-toolbar-title>
          <q-space />



          <!-- Interaction Mode Buttons -->
          <q-btn
            flat
            dense
            @click="setInteractionMode('automated')"
            :color="interactionMode === 'automated' ? 'yellow-6' : 'white'"
            icon="mdi-robot-happy"
            label="Automated"
            class="q-mr-sm"
          />
          <q-btn
            flat
            dense
            @click="setInteractionMode('assisted')"
            :color="interactionMode === 'assisted' ? 'yellow-6' : 'white'"
            icon="mdi-account-voice"
            label="Assisted"
            class="q-mr-md"
          />



          <!-- Provide Input Button -->
          <q-btn
            v-if="userInputRequiredByBackend && !isWaitingForInput"
            @click="isWaitingForInput = true"
            color="yellow-6"
            text-color="black"
            icon="mdi-pencil"
            label="Provide Input"
            dense
            class="q-mr-md"
          />

          <!-- Cancel Button -->
          <q-btn
            flat
            dense
            round
            icon="mdi-stop-circle-outline"
            aria-label="Cancel"
            @click="confirmKillProcess"
            v-if="isProcessRunning"
          >
            <q-tooltip>Cancel Process</q-tooltip>
          </q-btn>

          <q-tabs v-model="currentTab" dense active-color="white" indicator-color="white" align="right">
            <q-route-tab name="home" to="/" label="Home" icon="home" class="text-white" />
            <q-route-tab name="blackboard" to="/blackboard" label="Blackboard" icon="description" class="text-white" />
          </q-tabs>
        </q-toolbar>
        <q-linear-progress :value="1" indeterminate color="accent" v-if="isLoading && !isWaitingForInput" />
      </q-header>

      <!-- Drawers -->
      <q-drawer v-if="isBlackboardRoute" side="left" v-model="leftDrawerOpen" bordered :width="400" class="bg-grey-1 q-pa-md">
        <events-panel v-if="blackboardEvents && blackboardEvents.length > 0" :events="blackboardEvents" class="full-height-card"></events-panel>
        <div v-else class="text-center q-pa-md text-grey-6"><q-icon name="hourglass_empty" size="2em" /><div>No events yet.</div></div>
      </q-drawer>
      <q-drawer v-if="isBlackboardRoute" side="right" v-model="rightDrawerOpen" bordered :width="400" class="bg-grey-1 q-pa-md">
        <records-list v-if="blackboardRecords && blackboardRecords.length > 0" :records="blackboardRecords" class="full-height-card"></records-list>
        <div v-else class="text-center q-pa-md text-grey-6"><q-icon name="hourglass_empty" size="2em" /><div>No records yet.</div></div>
      </q-drawer>
      
      <q-page-container>
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.path" 
              :status="status" 
              :is-loading="isLoading"
              @start-flow="startDevopsFlow"
              @update-drawers="updateBlackboardDrawers" />
          </transition>
        </router-view>
      </q-page-container>

      <!-- User Input Modal -->
      <q-dialog v-model="isWaitingForInput">
        <q-card style="width: 500px;">
          <q-card-section class="bg-primary text-white">
            <div class="text-h6"><q-icon name="pan_tool" class="q-mr-sm" />User Input Required</div>
          </q-card-section>
          <q-card-section class="q-pt-none q-mt-md">
            <p>The process is paused at step: <strong>{{ waitingStepName }}</strong></p>
            <q-input 
              v-model="userFeedback" 
              :label="showApproveReject ? 'Your feedback (optional)' : 'Your feedback'" 
              type="textarea" 
              outlined 
              rows="3" 
              autogrow 
              :hint="showApproveReject ? 'Type your feedback and click Approve or Improve' : 'Type your feedback and click Resume'"
            />
          </q-card-section>
          <q-card-actions align="right" class="q-pa-md">
            <!-- Show Approve/Reject buttons for specific flows -->
            <template v-if="showApproveReject">
              <q-btn flat label="Improve" color="warning" @click="handleReject" class="q-mr-sm" />
              <q-btn flat label="Approve" color="positive" @click="handleApprove" />
            </template>
            <!-- Show standard Resume button for other flows -->
            <q-btn v-else flat label="Resume" color="primary" @click="handleResume" />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </q-layout>
  `,
  
  data() {
    return {
      currentTab: 'home',
      leftDrawerOpen: true,
      rightDrawerOpen: true,
      blackboardEvents: [],
      blackboardRecords: [],
      // Global state for interaction & process
      interactionMode: localStorage.getItem('interactionMode') || 'assisted',
      blackboard: {
        interaction: {
          mode: localStorage.getItem('interactionMode') || 'assisted',
        }
      },
      isLoading: false,
      status: '', // Will hold the status message string
      isProcessRunning: false,
      isWaitingForInput: false, // Controls the visibility of the input modal
      userInputRequiredByBackend: false, // Tracks if the backend is in a waiting state
      waitingStepName: '',
      userFeedback: '',
      statusPoller: null,
      justResumed: false, // Flag to prevent immediate pop-up reappearance
      showApproveReject: false, // Controls visibility of approve/reject buttons
      currentStepType: '' // Tracks the type of the current step (e.g., 'initial_research', 'per_resource_research')
    };
  },

  methods: {
    // --- Flow Management ---
    async startDevopsFlow(prompt) {
      if (!prompt.trim()) return;
      this.isLoading = true;
      this.blackboardEvents = []; // Clear previous events
      try {
        await this.$api.startDevopsFlow(prompt);
        this.startPolling();
        this.$router.push('/blackboard');
        this.$q.notify({ type: 'positive', message: 'DevopsFlow started. Navigating to Blackboard...', position: 'top-left' });
      } catch (error) {
        console.error('Error starting DevopsFlow:', error);
        this.$q.notify({ type: 'negative', message: 'Failed to start DevopsFlow.', position: 'top-left' });
        this.isLoading = false;
      }
    },
    confirmKillProcess() {
      this.$q.dialog({
        title: 'Confirm',
        message: 'Are you sure you want to cancel the running process?',
        cancel: true,
        persistent: true
      }).onOk(() => {
        this.killProcess();
      });
    },

    async killProcess() {
      this.$q.loading.show({
        message: 'Cancelling process... This may take a moment.',
        boxClass: 'bg-grey-2 text-grey-9',
        spinnerColor: 'primary'
      });
      this.stopPolling(); // Stop the regular poller

      try {
        await this.$api.killProcess();
        this.$q.notify({ type: 'info', message: 'Cancellation signal sent. Waiting for confirmation...', position: 'top-left' });

        // Poll aggressively until the process is confirmed dead.
        const deathPoller = setInterval(async () => {
          try {
            const { data } = await this.$api.getStatus();
            if (!data.is_running) {
              clearInterval(deathPoller);
              this.$q.loading.hide();
              this.isProcessRunning = false;
              this.isLoading = false;
              this.status = 'Process cancelled successfully.';
              this.$q.notify({ type: 'positive', message: 'Process successfully cancelled.', position: 'top-left' });
            }
          } catch (error) {
            // If getStatus fails, it might mean the server went down or the process is gone.
            clearInterval(deathPoller);
            this.$q.loading.hide();
            this.isProcessRunning = false;
            this.isLoading = false;
            this.status = 'Process cancelled.';
            this.$q.notify({ type: 'warning', message: 'Could not confirm cancellation status. Assuming process is stopped.', position: 'top-left' });
          }
        }, 2000); // Poll every 2 seconds
      } catch (error) {
        console.error('Error sending kill signal:', error);
        this.$q.loading.hide();
        this.$q.notify({ type: 'negative', message: 'Failed to send cancellation signal.', position: 'top-left' });
        this.startPolling(); // Resume normal polling if kill signal failed
      }
    },

    // --- Feedback Handling ---
    async handleResume() {
      await this.submitFeedback(this.userFeedback || 'No feedback provided');
    },
    
    // Handle approve action
    async handleApprove() {
      await this.submitFeedback('approve');
    },
    
    // Handle reject action
    async handleReject() {
      await this.submitFeedback(this.userFeedback || 'No feedback provided');
    },
    
    // Submit feedback to the backend
    async submitFeedback(feedback) {
      this.isLoading = true;
      this.justResumed = true; // Set flag to prevent immediate re-triggering
      
      try {
        await this.$api.resumeFlow(feedback);
        this.isWaitingForInput = false;
        this.userFeedback = ''; // Clear the input field after sending
        this.showApproveReject = false; // Reset the approve/reject UI state
        
        // Small delay to allow the backend to process the resume
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Reset the flag after a short delay
        setTimeout(() => {
          this.justResumed = false;
        }, 2000);
        
      } catch (error) {
        console.error('Error resuming flow:', error);
        this.$q.notify({ 
          type: 'negative', 
          message: 'Failed to submit feedback. Please try again.', 
          position: 'top-left' 
        });
      } finally {
        this.isLoading = false;
      }
    },

    // --- Polling and Status ---
    startPolling() {
      this.stopPolling();
      this.isLoading = true;
      // Bind checkStatus to maintain 'this' context
      const checkStatusBound = async () => {
        try {
          await this.checkStatus();
        } catch (error) {
          console.error('Error in status check:', error);
        }
      };
      
      // Initial status check
      checkStatusBound();
      
      // Set up interval for polling
      this.statusPoller = setInterval(checkStatusBound, 3000);
      
      console.log('Polling started');
    },
    
    stopPolling() {
      if (this.statusPoller) {
        clearInterval(this.statusPoller);
        this.statusPoller = null;
      }
    },
    
    async checkStatus() {
      try {
        const [{ data: statusData }, { data: interactionData }] = await Promise.all([
          this.$api.getStatus(),
          this.$api.getInteractionStatus()
        ]);

        const wasRunning = this.isProcessRunning;

        this.status = statusData.status || '';
        this.isProcessRunning = statusData.is_running || false;

        if (interactionData.interaction && interactionData.blackboard) {
          this.phase = interactionData.blackboard.phase;
          this.iterations = interactionData.blackboard.iterations;
          this.lastUpdated = new Date().toLocaleTimeString();
          if (interactionData.blackboard.events && Array.isArray(interactionData.blackboard.events.events)) {
            this.blackboardEvents = interactionData.blackboard.events.events;
          } else {
            this.blackboardEvents = [];
          }
          this.blackboard.interaction = interactionData.interaction;
          this.interactionMode = interactionData.interaction.mode;
          
          // Check if we should show approve/reject buttons based on the current step
          if (statusData.is_waiting_for_input) {
            this.waitingStepName = statusData.step_name || 'Unknown step';
            this.showApproveReject = this.shouldShowApproveReject(this.waitingStepName);
          }
        }

        // If the process is no longer running, update the UI accordingly
        if (wasRunning && !this.isProcessRunning) {
          this.stopPolling();
          this.isLoading = false;
          this.isWaitingForInput = false;
          this.userInputRequiredByBackend = false;
          this.showApproveReject = false;
          this.$q.notify({ type: 'info', message: 'Process finished.', position: 'top-left' });
          return; // No need to check for input if process is done
        }

        // Only show the input dialog if we're not in the middle of processing a response
        // and the backend is actually waiting for input
        if (statusData.is_waiting_for_input && !this.justResumed) {
          // Only update the waiting state if it's a new request for input
          if (!this.userInputRequiredByBackend) {
            this.stopPolling();
            this.isWaitingForInput = true;
            this.userInputRequiredByBackend = true;
            this.waitingStepName = statusData.step_name || 'Unknown step';
            this.isLoading = false;
            // Determine if we should show approve/reject buttons
            this.showApproveReject = this.shouldShowApproveReject(this.waitingStepName);
          }
        } else if (!statusData.is_waiting_for_input) {
          // Clear all input states if backend is not waiting for input
          if (this.userInputRequiredByBackend || this.isWaitingForInput) {
            this.userInputRequiredByBackend = false;
            this.isWaitingForInput = false;
            this.showApproveReject = false;
          }
        }

        this.isLoading = this.isProcessRunning && !this.isWaitingForInput;

      } catch (error) {
        if (this.isProcessRunning) {
          console.error('Status check failed:', error);
        }
        this.stopPolling();
        this.isLoading = false;
        this.isProcessRunning = false;
        this.status = '';
      }
    },
    
    // Determine if we should show approve/reject buttons based on the step name
    shouldShowApproveReject(stepName) {
      // Show approve/reject for research and review steps
      return stepName.includes('initial_research') || 
             stepName.includes('per_resource_research') ||
             stepName.includes('project_structure_review') ||
             stepName.includes('image_retrieval_review') ||
             stepName.includes('resource_') && stepName.includes('_research_review');
    },

    async setInteractionMode(mode) {
      try {
        await this.$api.setInteractionMode(mode);
        this.interactionMode = mode;
        this.blackboard.interaction.mode = mode; // Update blackboard for instant UI feedback
        localStorage.setItem('interactionMode', mode);
        this.$q.notify({
          type: 'info',
          message: `Mode set to ${mode}`,
          position: 'top-left',
          timeout: 2000
        });
      } catch (error) {
        console.error('Error setting interaction mode:', error);
        this.$q.notify({ type: 'negative', message: 'Failed to set interaction mode.', position: 'top-left' });
      }
    },
    updateBlackboardDrawers(data) {
      // This is called by child pages that might pass the whole blackboard
      if (data.events && Array.isArray(data.events.events)) {
        this.blackboardEvents = data.events.events;
      } else if (Array.isArray(data.events)) {
        // Or it might pass the events array directly
        this.blackboardEvents = data.events;
      }

      if (data.records) {
        this.blackboardRecords = data.records;
      }
    }
  },

  components: {
    'events-panel': window.components?.EventsPanel || { template: '<div></div>' },
    'records-list': window.RecordsList || { template: '<div></div>' },
  },

  computed: {
    isBlackboardRoute() {
      return this.$route.path === '/blackboard';
    }
  },

  watch: {
    '$route.path': {
      immediate: true,
      handler(newPath) {
        this.currentTab = newPath === '/' ? 'home' : 'blackboard';
        // Hide drawers if not on blackboard page
        if (newPath !== '/blackboard') {
          this.leftDrawerOpen = false;
          this.rightDrawerOpen = false;
        } else {
          // Ensure drawers are open when navigating to the blackboard
          this.leftDrawerOpen = true;
          this.rightDrawerOpen = true;
        }
      }
    }
  },

  created() {
    // Set the mode on the backend when the app loads
    this.setInteractionMode(this.interactionMode);
    
    // Start polling for status updates
    this.startPolling();
    
    // Also check status immediately
    this.checkStatus();
    
    // Set up a timer to restart polling if it stops (safety net)
    setInterval(() => {
      if (!this.statusPoller && this.isProcessRunning) {
        console.log('Restarting polling...');
        this.startPolling();
      }
    }, 5000); // Check every 5 seconds if polling has stopped
  }
});

// Global error handler
app.config.errorHandler = (err) => {
  console.error('Vue error:', err);
  Quasar.Notify.create({
    type: 'negative',
    message: 'An error occurred in the application.',
    position: 'top-left',
    timeout: 3000
  });  
};

// Make the apiService available globally as $api
app.config.globalProperties.$api = window.apiService;

// Use the Quasar plugin and provide configuration
app.use(Quasar, {
  plugins: {
    Notify: Quasar.Notify,
    Loading: Quasar.Loading,
    Dialog: Quasar.Dialog
  } 
});

// Use other plugins
app.use(window.router);

// Mount the application
app.mount('#q-app');

// Log application initialization
console.log('DevopsFlow application initialized');
