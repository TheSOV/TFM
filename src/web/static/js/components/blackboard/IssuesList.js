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
    <q-card class="shadow-1 full-height-card">
      <q-card-section class="bg-red-8 text-white">
        <div class="text-h6"><q-icon name="error" class="q-mr-sm" />Issues</div>
      </q-card-section>
      <q-separator />
      <q-card-section v-if="hasIssues" class="scrollable-card-section" style="padding: 0;">
        <q-list separator>
          <q-item 
            v-for="(issue, index) in issues" 
            :key="'issue-' + index"
            class="q-pa-md column"
          >
            <!-- Header Section -->
            <div class="row items-center q-mb-sm full-width">
              <q-icon :name="getSeverityIcon(issue.severity)" :color="getSeverityColor(issue.severity)" size="sm" class="q-mr-md" />
              <div class="col text-weight-bold ellipsis">
                {{ issue.issue || 'No title' }}
                <q-tooltip>{{ issue.issue }}</q-tooltip>
              </div>
              <q-badge :color="getSeverityColor(issue.severity)" :label="issue.severity" class="q-ml-md" />
              <q-badge v-if="issue.created_at" color="grey-7" :label="formatTime(issue.created_at)" class="q-ml-sm" dense />
            </div>

            <!-- Content Section -->
            <div class="full-width q-pl-xl">
              <div v-if="issue.problem_description" class="text-body2 text-grey-8 q-mb-sm" style="white-space: pre-wrap; word-wrap: break-word;">
                {{ issue.problem_description }}
              </div>
              <div v-if="issue.possible_manifest_file_path" class="text-caption text-grey-7 q-mb-xs">
                <q-icon name="description" size="xs" class="q-mr-xs" />
                <strong>File:</strong> {{ issue.possible_manifest_file_path }}
              </div>
              <div v-if="issue.observations" class="text-caption text-grey-7">
                <q-icon name="comment" size="xs" class="q-mr-xs" />
                <strong>Observations:</strong> {{ issue.observations }}
              </div>
            </div>
          </q-item>
        </q-list>
      </q-card-section>
      <q-card-section v-else class="flex flex-center text-grey-6 q-pa-md">
        <div>
          <q-icon name="check_circle_outline" size="2em" class="block q-mb-sm" />
          No issues reported.
        </div>
      </q-card-section>
    </q-card>
  `
};
