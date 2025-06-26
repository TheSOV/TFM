/**
 * EventsPanel Component
 * Displays a list of events in a collapsible panel
 */

// Register the component with the window object
if (!window.components) window.components = {};

window.components.EventsPanel = {
  name: 'EventsPanel',
  
  props: {
    events: {
      type: Array,
      default: () => []
    },
    maxChars: {
      type: Number,
      default: 150
    }
  },
  
  data() {
    return {
      expanded: {}
    };
  },
  
  computed: {
    sortedEvents() {
      if (!this.events || this.events.length === 0) {
        return [];
      }
      // Sort events by timestamp in descending order (newest first)
      return [...this.events].sort((a, b) => {
        const dateA = a.data && a.data.timestamp ? new Date(a.data.timestamp) : new Date(0);
        const dateB = b.data && b.data.timestamp ? new Date(b.data.timestamp) : new Date(0);
        return dateB - dateA;
      });
    }
  },
  
  methods: {
    formatTimestamp(timestamp) {
      if (!timestamp) return 'No timestamp';
      return new Date(timestamp).toLocaleString();
    },
    
    formatEventType(type) {
      if (!type) return 'Unknown Event';
      return type
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
    },

    togglePanel() {
      this.panelExpanded = !this.panelExpanded;
    },
    
    getEventIcon(eventType) {
      const icons = {
        'task_started': 'mdi-play-circle-outline',
        'task_completed': 'mdi-check-circle-outline',
      };
      return icons[eventType] || 'mdi-information-outline';
    },
    
    getEventColor(eventType) {
      const colors = {
        'task_started': 'blue',
        'task_completed': 'green',
      };
      return colors[eventType] || 'grey';
    },

    toggleExpand(eventId, field) {
      if (!this.expanded[eventId]) {
        this.expanded[eventId] = { description: false, output: false };
      }
      this.expanded[eventId][field] = !this.expanded[eventId][field];
    },

    isExpanded(eventId, field) {
      return this.expanded[eventId] && this.expanded[eventId][field];
    },

    truncate(text) {
      if (!text) return '';
      if (text.length > this.maxChars) {
        return text.substring(0, this.maxChars) + '...';
      }
      return text;
    }
  },
  
  template: `
    <div class="events-panel-container">
      <div class="q-pa-sm q-pl-md bg-grey-3 text-grey-9 text-weight-bold row items-center">
        <q-icon name="mdi-history" class="q-mr-sm" />
        <span>Events</span>
      </div>
      <q-list separator class="bg-white" style="max-height: calc(100vh - 40px); overflow-y: auto;">
        <q-item 
          v-for="event in sortedEvents" 
          :key="event.data.timestamp"
          class="q-py-sm q-px-md"
        >
          <q-item-section avatar top class="q-pr-md q-pt-sm">
            <q-icon 
              :name="getEventIcon(event.data.type)" 
              :color="getEventColor(event.data.type)"
              size="28px"
            />
          </q-item-section>
          
          <q-item-section>
            <q-item-label class="text-weight-medium">
              {{ formatEventType(event.data.type) }}
              <q-tooltip>{{ event.data.type }}</q-tooltip>
            </q-item-label>
            <q-item-label caption class="q-mb-xs">
              {{ formatTimestamp(event.data.timestamp) }}
            </q-item-label>

            <!-- Agent Role -->
            <q-item-label v-if="event.data.agent_role" class="text-caption text-grey-8 q-mb-sm">
              <q-icon name="mdi-account-tie" size="xs" class="q-mr-xs"/>
              {{ event.data.agent_role }}
            </q-item-label>

            <!-- Task Description -->
            <div v-if="event.data.task_description" class="q-mb-sm text-grey-9 content-block">
              <div class="row items-center q-mb-xs">
                <p class="text-weight-bold q-ma-none">Description</p>
                <a v-if="event.data.task_description.length > maxChars" @click.stop="toggleExpand(event.data.timestamp, 'description')" class="text-primary cursor-pointer q-ml-sm text-caption">
                  {{ isExpanded(event.data.timestamp, 'description') ? 'Show less' : 'Show more' }}
                </a>
              </div>
              <div class="content-text" style="white-space: pre-wrap; word-wrap: break-word; font-size: 0.85em;">
                {{ isExpanded(event.data.timestamp, 'description') ? event.data.task_description : truncate(event.data.task_description) }}
              </div>
            </div>

            <!-- Task Output -->
            <div v-if="event.data.output" class="text-grey-9 content-block">
              <div class="row items-center q-mb-xs">
                <p class="text-weight-bold q-ma-none">Output</p>
                <a v-if="event.data.output.length > maxChars" @click.stop="toggleExpand(event.data.timestamp, 'output')" class="text-primary cursor-pointer q-ml-sm text-caption">
                  {{ isExpanded(event.data.timestamp, 'output') ? 'Show less' : 'Show more' }}
                </a>
              </div>
              <div class="content-text" style="white-space: pre-wrap; word-wrap: break-word; font-size: 0.85em;">
                {{ isExpanded(event.data.timestamp, 'output') ? event.data.output : truncate(event.data.output) }}
              </div>
            </div>
          </q-item-section>
        </q-item>
        <q-item v-if="!sortedEvents.length">
          <q-item-section class="text-center text-grey-6 q-py-lg">
            <q-icon name="hourglass_empty" size="2em" class="q-mb-sm" />
            <div>No events recorded yet.</div>
          </q-item-section>
        </q-item>
      </q-list>
          </q-item>
        </q-list>
      </q-expansion-item>
    </div>
  `
};
