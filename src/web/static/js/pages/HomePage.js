/**
 * HomePage.js
 * 
 * This component renders the main user interface for starting a DevopsFlow process.
 * It is a 'dumb' component that receives its state via props from the main app component
 * and emits an event to trigger the start of a flow.
 */
const HomePage = {
  template: `
    <q-page class=\"flex flex-center column q-pa-md bg-grey-2\">
      <q-card class=\"q-pa-md shadow-2\" style=\"width: 100%; max-width: 800px;\">
        <q-card-section class=\"text-center\">
          <div class=\"text-h4 text-primary text-weight-bold\">Start a New Devops Flow</div>
          <div class=\"text-subtitle1 text-grey-7 q-mt-sm\">Enter a prompt to begin the automated DevOps process.</div>
        </q-card-section>

        <q-card-section>
          <q-input
            v-model=\"prompt\"
            label=\"Your Prompt (e.g., 'deploy a hello world app on k8s')\"
            outlined
            autogrow
            :disable=\"isBusy\"
            @keydown.enter.exact.prevent=\"submitPrompt\"
            class=\"q-mb-md\"
          >
            <template v-slot:prepend>
              <q-icon name=\"input\" />
            </template>
          </q-input>
          <q-btn 
            label=\"Start Flow\"
            color=\"primary\"
            @click=\"submitPrompt\"
            :loading=\"isLoading\"
            :disable=\"isBusy || !prompt.trim()\"
            class=\"full-width\"
            size=\"lg\"
            icon-right=\"send\"
          />
        </q-card-section>
      </q-card>

      <!-- Status Card -->
      <q-card v-if=\"isBusy\" class=\"q-mt-lg q-pa-sm shadow-2 bg-grey-3\" style=\"width: 100%; max-width: 800px;\">
        <q-card-section class=\"row items-center no-wrap\">
          <q-spinner color=\"primary\" size=\"2em\" class=\"q-mr-md\" />
          <div class=\"text-weight-medium text-primary\">
            Process is running... 
            <span v-if=\"status.message\" class=\"text-grey-8\">{{ status.message }}</span>
          </div>
        </q-card-section>
      </q-card>

    </q-page>
  `,
  props: {
    status: {
      type: Object,
      required: true
    },
    isLoading: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      prompt: '',
    };
  },
  computed: {
    isBusy() {
      // The form should be disabled if the global state is loading OR if a process is running.
      return this.isLoading || this.status.is_running;
    }
  },
  methods: {
    submitPrompt() {
      if (!this.prompt.trim() || this.isBusy) return;
      this.$emit('start-flow', this.prompt);
    },
  },
};

window.HomePage = HomePage;

// This module provides the HomePage component for the DevopsFlow application.
// It includes a form to start a new DevopsFlow process, displays the current status, and handles user interaction for assisted mode.
