console.log('PlansDisplay.js: typeof window.showdown =', typeof window.showdown);
console.log('PlansDisplay.js: typeof window.marked =', typeof window.marked);

/**
 * PlansDisplay Component
 * Displays buttons to show Basic and Advanced plans in a dialog.
 */
window.PlansDisplay = {
  name: 'PlansDisplay',
  props: {
    basicPlan: {
      type: String,
      default: ''
    },
    advancedPlan: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      showDialog: false,
      planTitle: '',
      planContent: ''
    };
  },
  computed: {
    formattedPlanContent() {
      if (this.planContent && typeof this.planContent === 'string') {
        let contentToParse = this.planContent;
        const trimmedContent = contentToParse.trim();
        // Check if the entire content is wrapped in triple backticks
        if (trimmedContent.startsWith('```') && trimmedContent.endsWith('```')) {
          // Attempt to remove the outer triple backticks
          // Only do this if it seems to be a wrapper for the whole content,
          // not a legit code block that happens to be at the start/end of a larger document.
          // A simple heuristic: check if there's another ``` inside after the first line and before the last line.
          // For now, a simpler removal if it's the common case of the whole thing being a block:
          const lines = trimmedContent.split('\n');
          if (lines.length > 1) { // Ensure it's not just '```code```'
             contentToParse = trimmedContent.substring(3, trimmedContent.length - 3).trim();
          }
        }

        if (typeof window.showdown !== 'undefined' && typeof window.showdown.Converter === 'function') {
          console.log('PlansDisplay.js: Using showdown for Markdown.');
          const converter = new showdown.Converter();
          return converter.makeHtml(this.planContent);
        } else if (typeof window.marked === 'object' && typeof window.marked.parse === 'function') {
          console.log('PlansDisplay.js: Using marked.parse for Markdown.');
          return window.marked.parse(contentToParse);
        } else {
          console.warn('PlansDisplay.js: No Markdown library (showdown or marked) available. Displaying raw plan content.');
          return `<pre style="white-space: pre-wrap; word-wrap: break-word;">${contentToParse}</pre>`;
        }
      }
      return '';
    },

    hasBasicPlan() {
      return !!this.basicPlan;
    },
    hasAdvancedPlan() {
      return !!this.advancedPlan;
    }
  },
  methods: {
    openPlanDialog(type) {
      if (type === 'basic' && this.hasBasicPlan) {
        this.planTitle = 'Basic Plan';
        this.planContent = this.basicPlan;
        this.showDialog = true;
      } else if (type === 'advanced' && this.hasAdvancedPlan) {
        this.planTitle = 'Advanced Plan';
        this.planContent = this.advancedPlan;
        this.showDialog = true;
      }
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-blue-grey-1">
        <div class="text-h6"><q-icon name="article" class="q-mr-sm" />Plans</div>
      </q-card-section>
      <q-separator />
      <q-card-section class="column q-gutter-y-md scrollable-card-section">
        <q-btn 
          label="Basic Plan" 
          color="info" 
          @click="openPlanDialog('basic')" 
          :disable="!hasBasicPlan" 
          icon="visibility"
          stretch
        />
        <q-btn 
          label="Advanced Plan" 
          color="purple" 
          @click="openPlanDialog('advanced')" 
          :disable="!hasAdvancedPlan" 
          icon="visibility"
          stretch
        />
      </q-card-section>

      <q-dialog v-model="showDialog">
        <q-card style="width: 900px; max-width: 90vw;">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ planTitle }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-card-section style="max-height: 70vh; overflow-y: auto;" class="markdown-content">
            <div v-if="planContent" v-html="formattedPlanContent"></div>
            <div v-else class="text-grey-7">No plan content available.</div>
          </q-card-section>
        </q-card>
      </q-dialog>
    </q-card>
  `
};
