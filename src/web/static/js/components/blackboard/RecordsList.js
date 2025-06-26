/**
 * RecordsList Component
 * Displays a scrollable list of records.
 */
window.RecordsList = {
  name: 'RecordsList',
  props: {
    records: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    hasRecords() {
      return this.records && this.records.length > 0;
    },
    reversedRecords() {
      return this.records ? this.records.slice().reverse() : [];
    }
  },
  methods: {
    formatTime(timestamp) {
      if (!timestamp) return 'N/A';
      // Plain HH:MM:SS string?
      if (typeof timestamp === 'string' && /^\d{2}:\d{2}:\d{2}$/.test(timestamp.trim())) {
        return timestamp;
      }
      let ms;
      if (typeof timestamp === 'number') {
        // If the timestamp is already in milliseconds (> 1e12) keep it, otherwise assume seconds and convert
        ms = timestamp > 1e12 ? timestamp : timestamp * 1000;
      } else if (typeof timestamp === 'string') {
        // Attempt to parse numeric strings as epoch, otherwise fall back to Date.parse()
        const num = Number(timestamp);
        if (!isNaN(num)) {
          ms = num > 1e12 ? num : num * 1000;
        } else {
          ms = Date.parse(timestamp);
        }
      } else {
        return 'Invalid date';
      }
      const dt = new Date(ms);
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },
    getRecordTypeColor(type) {
      switch (type?.toLowerCase()) {
        case 'info': return 'info';
        case 'warning': return 'warning';
        case 'error': return 'negative';
        case 'success': return 'positive';
        case 'debug': return 'grey';
        case 'devops_engineer': return 'deep-purple';
        default: return 'primary';
      }
    },
    getRecordTypeIcon(type) {
      switch (type?.toLowerCase()) {
        case 'info': return 'info';
        case 'warning': return 'warning';
        case 'error': return 'error_outline';
        case 'success': return 'check_circle_outline';
        case 'debug': return 'bug_report';
        case 'action': return 'mdi-play-circle-outline';
        case 'milestone': return 'flag';
        case 'deletion': return 'delete_sweep';
        case 'devops_engineer': return 'engineering';
        default: return 'notes';
      }
    },
    formatDetails(details) {
      if (!details) return '';
      if (typeof details === 'object') {
        return JSON.stringify(details, null, 2);
      }
      return details;
    }
  },
  template: `
    <div class="records-panel-container">
      <div class="q-pa-sm q-pl-md bg-grey-3 text-grey-9 text-weight-bold row items-center">
        <q-icon name="article" class="q-mr-sm" />
        <span>Records</span>
      </div>
      <q-list separator class="bg-white" style="max-height: calc(100vh - 40px); overflow-y: auto;">
        <q-item 
          v-for="(record, index) in reversedRecords" 
          :key="index"
          class="q-py-sm q-px-md"
        >
          <q-item-section avatar top class="q-pr-md q-pt-xs">
            <q-icon :name="getRecordTypeIcon(record.agent)" :color="getRecordTypeColor(record.agent)" size="28px" />
          </q-item-section>

          <q-item-section>
            <q-item-label class="text-weight-medium" style="word-break: break-word; white-space: normal;">
              {{ record.task_description || 'No description' }}
            </q-item-label>
            <q-item-label caption class="q-mt-xs">
              <q-badge :color="getRecordTypeColor(record.agent)" :label="record.agent || 'N/A'" />
              <q-badge v-if="record.created_at" color="grey-7" :label="formatTime(record.created_at)" class="q-ml-sm" dense />
            </q-item-label>
            <q-item-label caption v-if="record.details" class="q-mt-sm">
              <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit; font-size: 0.8em; color: #555;">{{ formatDetails(record.details) }}</pre>
            </q-item-label>
          </q-item-section>
        </q-item>
        <q-item v-if="!hasRecords">
          <q-item-section class="text-center text-grey-6 q-py-lg">
            <q-icon name="hourglass_empty" size="2em" class="q-mb-sm" />
            <div>No records to display.</div>
          </q-item-section>
        </q-item>
      </q-list>
    </div>
  `
};
