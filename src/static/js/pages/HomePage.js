/**
 * Home Page Component
 * Displays the main form to start a new DevopsFlow
 */

export default {
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
          
          <q-card-actions v-if="status.is_running !== null" align="right" class="q-px-md q-pb-md q-pt-sm">
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

  methods: {
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
