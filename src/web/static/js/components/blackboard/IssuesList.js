/**
 * IssuesList Component
 * Displays a scrollable list of issues.
 */
window.IssuesList = {
  name: 'IssuesList',
  props: {
    issues: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    hasIssues() {
      return this.issues && this.issues.length > 0;
    }
  },
  methods: {
    getSeverityColor(severity) {
      switch (severity?.toLowerCase()) {
        case 'critical': return 'negative';
        case 'high': return 'deep-orange';
        case 'medium': return 'warning';
        case 'low': return 'info';
        default: return 'grey-7';
      }
    },
    getSeverityIcon(severity) {
      switch (severity?.toLowerCase()) {
        case 'critical': return 'mdi-alert-octagon';
        case 'high': return 'mdi-alert';
        case 'medium': return 'mdi-alert-circle-outline';
        case 'low': return 'mdi-information-outline';
        default: return 'mdi-help-circle-outline';
      }
    },
    formatTime(timestamp) {
      if (!timestamp) return '';
      // If we already get a plain HH:MM:SS string, return it directly
      if (typeof timestamp === 'string' && /^\d{2}:\d{2}:\d{2}$/.test(timestamp.trim())) {
        return timestamp;
      }
      let ms;
      if (typeof timestamp === 'number') {
        ms = timestamp > 1e12 ? timestamp : timestamp * 1000;
      } else if (typeof timestamp === 'string') {
        const num = Number(timestamp);
        if (!isNaN(num)) {
          ms = num > 1e12 ? num : num * 1000;
        } else {
          ms = Date.parse(timestamp);
        }
      } else {
        return '';
      }
      const dt = new Date(ms);
      // Return only the time portion for display consistency
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section style="background-color: rgba(193, 0, 21, 0.45);">
        <div class="text-h6"><q-icon name="error" class="q-mr-sm" />Issues</div>
      </q-card-section>
      <q-separator />
      <q-card-section v-if="hasIssues" class="scrollable-card-section" style="padding: 0;">
        
          <q-list bordered separator>
            <q-item 
              v-for="(issue, index) in issues" 
              :key="'issue-' + index"
            >
              <q-item-section avatar top>
                <q-icon :name="getSeverityIcon(issue.severity)" :color="getSeverityColor(issue.severity)" size="md" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold">
                  {{ issue.issue || 'No title' }}
                  <q-badge v-if="issue.created_at" color="grey" :label="formatTime(issue.created_at)" class="q-ml-sm" dense />
                </q-item-label>
                <q-item-label caption lines="3">{{ issue.problem_description || 'No description' }}</q-item-label>
                <q-item-label caption v-if="issue.possible_manifest_file_path" class="q-mt-sm">
                  <q-icon name="description" size="xs" class="q-mr-xs" />
                  File: {{ issue.possible_manifest_file_path }}
                </q-item-label>
                <q-item-label caption v-if="issue.observations">
                  <q-icon name="comment" size="xs" class="q-mr-xs" />
                  {{ issue.observations }}
                </q-item-label>
              </q-item-section>
              <q-item-section side top v-if="issue.severity">
                <q-badge :color="getSeverityColor(issue.severity)" :label="issue.severity" />
              </q-item-section>
            </q-item>
          </q-list>
        
      </q-card-section>
      <q-card-section v-else>
        <div class="text-grey-6 text-center q-pa-md">No issues reported.</div>
      </q-card-section>
    </q-card>
  `
};
