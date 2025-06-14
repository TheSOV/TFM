/**
 * Home Page Component
 * Displays the main form to start a new DevopsFlow
 */

window.HomePage = {
  name: 'HomePage',
  
  template: `
    <div class="page-container">
      <div class="card-container">
        <q-card class="q-pa-lg shadow-3">
          <q-card-section>
            <div class="text-h5 text-weight-bold q-mb-md">
              <q-icon name="mdi-robot" color="primary" class="q-mr-sm" />
              Start a New DevopsFlow
            </div>
            
            <q-separator class="q-mb-lg" />
            
            <q-form @submit.prevent="onSubmit" class="q-gutter-y-md">
              <div class="text-subtitle2 text-grey-8 q-mb-sm">
                Describe what you want to accomplish
              </div>
              
              <q-input
                v-model="prompt"
                filled
                type="textarea"
                label="Your prompt"
                :rules="[val => !!val || 'Please enter a prompt']"
                autogrow
                class="q-mb-md"
                :input-style="{ minHeight: '120px' }"
                placeholder="Example: Set up a CI/CD pipeline for my Python application..."
              />
              
              <div class="form-actions">
                <q-btn 
                  label="Start DevopsFlow" 
                  type="submit" 
                  color="primary" 
                  :loading="isLoading"
                  icon="play_arrow"
                  :disable="!prompt.trim()"
                  padding="12px 24px"
                  no-caps
                />
                
                <q-btn 
                  label="Clear" 
                  type="reset" 
                  color="grey-7" 
                  flat 
                  @click="prompt = ''"
                  :disable="!prompt.trim() || isLoading"
                  padding="12px 16px"
                  no-caps
                />
                
                <q-space />
                
                <q-btn 
                  label="View Blackboard" 
                  to="/blackboard" 
                  color="secondary" 
                  outline
                  icon="description"
                  padding="12px 16px"
                  no-caps
                />
              </div>
            </q-form>
          </q-card-section>
          
          <q-separator v-if="status.is_running !== null" class="q-mt-md" />
          
          <q-card-actions v-if="status.is_running !== null" align="right" class="q-px-md q-pb-md q-pt-sm d-flex justify-between items-center">
            <div class="text-caption text-grey-7">
              Status: 
              <q-badge 
                :color="status.is_running ? 'positive' : 'negative'" 
                class="q-ml-sm"
                text-color="white"
              >
                <q-icon :name="status.is_running ? 'check_circle' : 'stop_circle'" class="q-mr-xs" />
                {{ status.is_running ? 'Running' : 'Stopped' }}
              </q-badge>
            </div>
            <q-btn 
              v-if="status.is_running"
              label="Kill Process"
              color="negative"
              icon="power_settings_new"
              @click="killProcess"
              :loading="isLoading"
              :disable="isLoading"
              padding="8px 12px"
              size="sm"
              no-caps
            />
          </q-card-actions>
        </q-card>
        
        <div class="q-mt-lg text-center text-grey-7 text-caption">
          <div class="q-mb-xs">
            <q-icon name="info" size="xs" class="q-mr-xs" />
            Enter your task and let DevopsFlow handle the automation
          </div>
          <div>
            <q-icon name="history" size="xs" class="q-mr-xs" />
            Check the Blackboard for real-time updates
          </div>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      prompt: '',
      isLoading: false,
      status: { is_running: null }
    };
  },

  mounted() {
    this.checkStatus(); // Initial status check when component mounts
  },

  methods: {
    async killProcess() {
      this.isLoading = true; // Keep isLoading true for the whole duration
      try {
        const killApiResponse = await this.$api.killDevopsFlow();
        this.$q.notify({
          type: 'info',
          message: killApiResponse.data.message || 'Kill signal sent. Waiting for process to stop...',
          position: 'top'
        });

        // Start polling for status until it's no longer running
        const pollUntilStopped = async () => {
          await this.checkStatus(); // This updates this.status and schedules general polling if still running
          if (this.status.is_running) {
            // If still running, wait a bit and poll again specifically for the kill operation
            setTimeout(pollUntilStopped, 2000); // Poll every 2 seconds for kill confirmation
          } else {
            // Process has stopped
            this.$q.notify({
              type: 'positive',
              message: 'DevopsFlow process has stopped.',
              position: 'top'
            });
            this.isLoading = false; // Now set isLoading to false
          }
        };
        
        pollUntilStopped(); // Start the dedicated kill polling

      } catch (error) {
        console.error('Error killing DevopsFlow:', error);
        this.$q.notify({
          type: 'negative',
          message: error.response?.data?.message || 'Failed to send kill signal or error during stop confirmation.',
          position: 'top',
          timeout: 5000
        });
        this.isLoading = false; // Also set to false on error
      }
      // Note: isLoading is now managed by the pollUntilStopped logic or error case
    },

    async onSubmit() {
      if (!this.prompt.trim()) {
        return;
      }

      this.isLoading = true;
      
      try {
        const response = await this.$api.initDevopsFlow(this.prompt);
        this.$q.notify({
          type: 'positive',
          message: 'DevopsFlow started successfully',
          position: 'top'
        });
        this.status = { is_running: true };
        this.prompt = '';
      } catch (error) {
        console.error('Error starting DevopsFlow:', error);
        this.$q.notify({
          type: 'negative',
          message: error.response?.data?.message || 'Failed to start DevopsFlow',
          position: 'top',
          timeout: 5000
        });
      } finally {
        this.isLoading = false;
      }
    },

    async checkStatus() {
      try {
        const response = await this.$api.getStatus();
        this.status = response.data;
        if (this.status.is_running) {
          // If still running, poll again after a delay
          setTimeout(this.checkStatus, 5000); // Poll every 5 seconds
        }
      } catch (error) {
        console.error('Error checking status:', error);
      }
    }
  },

  created() {
    this.checkStatus();
  }
};

// This module provides the HomePage component for the DevopsFlow application.
// It includes a form to start a new DevopsFlow process and displays the current status.
