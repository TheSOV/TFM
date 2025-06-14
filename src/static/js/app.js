/**
 * Main Application Entry Point
 * Initializes the Vue 3 application with Quasar and Vue Router
 */

// Import Vue and Vue Router
import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';

// Import Quasar from CDN (loaded in index.html)
const { Quasar, Notify, Loading } = window.Quasar;

// Import application components and services
import router from './router/index.js';
import apiService from './services/api.js';

// Create the Vue application instance
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
  Notify.create({
    type: 'negative',
    message: 'An error occurred',
    position: 'top',
    timeout: 3000
  });  
};

// Global properties
app.config.globalProperties.$api = apiService;
app.config.globalProperties.$q = { Notify, Loading };

// Use plugins
app.use(Quasar, {
  plugins: { Notify, Loading },
  config: {
    brand: {
      primary: '#1976D2',
      secondary: '#26A69A',
      accent: '#9C27B0',
      dark: '#1D1D1D',
      positive: '#21BA45',
      negative: '#C10015',
      info: '#31CCEC',
      warning: '#F2C037'
    },
    notify: {},
    loading: {}
  }
});

// Use router
app.use(router);

// Mount the application
app.mount('#q-app');

// Log application initialization
console.log('DevopsFlow application initialized');
