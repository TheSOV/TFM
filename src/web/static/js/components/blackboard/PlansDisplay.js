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
      if (this.planContent) {
        if (typeof window.showdown !== 'undefined' && typeof window.showdown.Converter === 'function') {
          console.log('PlansDisplay.js: Using showdown for Markdown.');
          const converter = new showdown.Converter();
          return converter.makeHtml(this.planContent);
        } else if (typeof window.marked === 'function') {
          console.log('PlansDisplay.js: Using marked for Markdown (fallback).');
          return marked(this.planContent);
        } else {
          console.warn('PlansDisplay.js: No Markdown library (showdown or marked) available. Displaying raw plan content.');
          return `<pre style="white-space: pre-wrap; word-wrap: break-word;">${this.planContent}</pre>`;
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
