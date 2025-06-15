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
    <q-card class="shadow-1">
      <q-card-section class="bg-indigo-1">
        <div class="text-h6"><q-icon name="history" class="q-mr-sm" />Records</div>
      </q-card-section>
      <q-separator />
      <q-card-section v-if="hasRecords" class="scrollable-card-section" style="padding: 0; max-height: 95%; overflow-y: auto;">
        <q-list bordered separator>
            <q-item 
              v-for="(record, index) in reversedRecords" 
              :key="index"
            >
              <q-item-section avatar top>
                <q-icon :name="getRecordTypeIcon(record.agent)" :color="getRecordTypeColor(record.agent)" size="sm" />
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  <span class="text-weight-medium">{{ record.task_description || 'No description' }}</span>
                  <q-badge :color="getRecordTypeColor(record.agent)" :label="record.agent || 'N/A'" class="q-ml-sm" />
                  <q-badge v-if="record.created_at" color="grey" :label="formatTime(record.created_at)" class="q-ml-sm" dense />
                </q-item-label>
                <!-- Timestamp not available in this record type -->
                <q-item-label v-if="record.details && Object.keys(record.details).length > 0" caption class="q-mt-xs">
                  <div class="text-caption text-grey-7">Details:</div>
                  <pre style="white-space: pre-wrap; word-wrap: break-word; background-color: #f9f9f9; padding: 6px; border-radius: 3px; font-size: 0.75em; max-height: 80px; overflow-y: auto;">{{ formatDetails(record.details) }}</pre>
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
      </q-card-section>
      <q-card-section v-else>
        <div class="text-grey-6 text-center q-pa-md">No records available.</div>
      </q-card-section>
    </q-card>
  `
};
