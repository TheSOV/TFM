/**
 * Main Application Entry Point
 * Initializes the Vue 3 application with Quasar and Vue Router
 */
const { createApp } = Vue;

// The main Quasar object from the UMD script
const Quasar = window.Quasar;

const app = createApp({
  template: `
    <q-layout view="hHh lpr fff">
      <q-header elevated class="bg-primary text-white">
        <q-toolbar>
          <q-toolbar-title class="text-h5 text-weight-bold">
            <q-icon name="mdi-robot" class="q-mr-sm" />
            DevopsFlow
          </q-toolbar-title>
          <q-space />
          <q-tabs v-model="currentTab" dense active-color="white" indicator-color="yellow-6" align="right">
            <q-route-tab 
              name="home" 
              to="/" 
              label="Home" 
              icon="home" 
              class="text-white"
            />
            <q-route-tab 
              name="blackboard" 
              to="/blackboard" 
              label="Blackboard" 
              icon="description"
              class="text-white"
            />
          </q-tabs>
        </q-toolbar>
      </q-header>

      <!-- Left Drawer (for Blackboard) -->
      <q-drawer v-if="isBlackboardRoute" side="left" v-model="leftDrawerOpen" bordered :width="400" class="bg-grey-1 q-pa-md">
        <events-panel 
          v-if="blackboardEvents && blackboardEvents.length > 0"
          :events="blackboardEvents"
          :max-chars="300"
          class="full-height-card"
        ></events-panel>
        <div v-else class="text-center q-pa-md text-grey-6">
          <q-icon name="hourglass_empty" size="2em" />
          <div>No events yet.</div>
        </div>
      </q-drawer>

      <!-- Right Drawer (for Blackboard) -->
      <q-drawer v-if="isBlackboardRoute" side="right" v-model="rightDrawerOpen" bordered :width="400" class="bg-grey-1 q-pa-md">
        <records-list 
          v-if="blackboardRecords && blackboardRecords.length > 0"
          :records="blackboardRecords"
          class="full-height-card"
        ></records-list>
        <div v-else class="text-center q-pa-md text-grey-6">
          <q-icon name="hourglass_empty" size="2em" />
          <div>No records yet.</div>
        </div>
      </q-drawer>
      
      <q-page-container>
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.path" @update-drawers="updateBlackboardDrawers" />
          </transition>
        </router-view>
      </q-page-container>
    </q-layout>
  `,
  
  data() {
    return {
      currentTab: 'home',
      leftDrawerOpen: true,
      rightDrawerOpen: true,
      blackboardEvents: [],
      blackboardRecords: [],
    };
  },

  components: {
    'events-panel': window.components?.EventsPanel || { template: '<div></div>' },
    'records-list': window.RecordsList || { template: '<div></div>' },
  },

  computed: {
    isBlackboardRoute() {
      return this.$route.path === '/blackboard';
    }
  },

  watch: {
    '$route.path': {
      immediate: true,
      handler(newPath) {
        // Set the current tab based on the route name still
        this.currentTab = this.$route.name || 'home';
        
        // Explicitly show or hide drawers based on the path
        if (newPath === '/blackboard') {
          this.leftDrawerOpen = true;
          this.rightDrawerOpen = true;
        } else {
          this.leftDrawerOpen = false;
          this.rightDrawerOpen = false;
        }
      }
    }
  },

  methods: {
    updateBlackboardDrawers(data) {
      const events = data?.events?.events || [];
      this.blackboardEvents = events.slice().reverse();
      this.blackboardRecords = data?.records || [];
    }
  },
});

// Global error handler
app.config.errorHandler = (err) => {
  console.error('Vue error:', err);
  Quasar.Notify.create({
    type: 'negative',
    message: 'An error occurred in the application.',
    position: 'top',
    timeout: 3000
  });  
};

// Make the apiService available globally as $api
app.config.globalProperties.$api = window.apiService;

// Use the Quasar plugin and provide configuration
app.use(Quasar, {
  plugins: {
    Notify: Quasar.Notify,
    Loading: Quasar.Loading
  } 
});

// Use other plugins
app.use(window.router);

// Mount the application
app.mount('#q-app');

// Log application initialization
console.log('DevopsFlow application initialized');
