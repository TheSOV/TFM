window.UserRequestDisplay = {
  name: 'UserRequestDisplay',
  props: {
    request: {
      type: String,
      default: 'Not available'
    },
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
        // Basic check to remove outer triple backticks if they wrap the whole content
        if (trimmedContent.startsWith('```') && trimmedContent.endsWith('```')) {
          const lines = trimmedContent.split('\n');
          if (lines.length > 1 && lines[0].match(/^```\w*$/) && lines[lines.length -1] === '```') { // check if first line is ```lang and last is ```
             contentToParse = lines.slice(1, -1).join('\n');
          } else if (lines.length === 1 && lines[0].substring(3, lines[0].length - 3).indexOf('```') === -1) { // single line ```code```
             contentToParse = lines[0].substring(3, lines[0].length - 3);
          } else if (lines.length > 1 && lines[0] === '```' && lines[lines.length -1] === '```') { // simple ``` and ```
             contentToParse = lines.slice(1, -1).join('\n');
          }
        }

        if (typeof window.showdown !== 'undefined' && typeof window.showdown.Converter === 'function') {
          const converter = new showdown.Converter({
            ghCompatibleHeaderId: true,
            simpleLineBreaks: true,
            simplifiedAutoLink: true,
            strikethrough: true,
            tables: true,
            tasklists: true,
            openLinksInNewWindow: true,
            emoji: true
          });
          return converter.makeHtml(contentToParse);
        } else if (typeof window.marked === 'object' && typeof window.marked.parse === 'function') {
          return window.marked.parse(contentToParse);
        }
        return '<pre>' + contentToParse.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>';
      }
      return '';
    },
    hasBasicPlan() {
      return this.basicPlan && this.basicPlan.trim() !== '';
    },
    hasAdvancedPlan() {
      return this.advancedPlan && this.advancedPlan.trim() !== '';
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
        <div class="text-h6"><q-icon name="input" class="q-mr-sm" />User Request</div>
      </q-card-section>
      <q-separator />
      <q-card-section class="scrollable-card-section">
        <div class="text-body1" style="white-space: pre-wrap;">{{ request }}</div>
      </q-card-section>

      <template v-if="hasBasicPlan || hasAdvancedPlan">
        <q-separator />
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">Available Plans:</div>
          <div class="row q-gutter-sm">
            <q-btn 
              v-if="hasBasicPlan"
              label="View Basic Plan" 
              color="info" 
              outline
              @click="openPlanDialog('basic')" 
              icon="visibility"
              class="col"
            />
            <q-btn 
              v-if="hasAdvancedPlan"
              label="View Advanced Plan" 
              color="purple" 
              outline
              @click="openPlanDialog('advanced')" 
              icon="visibility"
              class="col"
            />
          </div>
        </q-card-section>
      </template>

      <q-dialog v-model="showDialog">
        <q-card style="width: 900px; max-width: 90vw;">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ planTitle }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-card-section style="max-height: 70vh; overflow-y: auto;" class="markdown-content q-pt-none">
            <div v-if="planContent" v-html="formattedPlanContent"></div>
            <div v-else class="text-grey-7">No plan content available.</div>
          </q-card-section>
        </q-card>
      </q-dialog>
    </q-card>
  `
};
