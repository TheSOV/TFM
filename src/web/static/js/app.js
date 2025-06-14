/**
 * Main Application Entry Point
 * Initializes the Vue 3 application with Quasar and Vue Router
 */
const { createApp } = Vue;

// The main Quasar object from the UMD script
const Quasar = window.Quasar;

const app = createApp({
  template: `
    <q-layout view="hHh Lpr lFf">
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
      
      <q-page-container>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </q-page-container>
    </q-layout>
  `,
  
  data() {
    return {
      currentTab: 'home'
    };
  }
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
