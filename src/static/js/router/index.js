/**
 * Router Configuration
 * Defines the application routes and their corresponding components
 */

import { createRouter, createWebHistory } from 'vue-router';

// Use dynamic imports for code splitting
const HomePage = () => import('../pages/HomePage.js');
const BlackboardPage = () => import('../pages/BlackboardPage.js');

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomePage,
    meta: {
      title: 'DevopsFlow - Home'
    }
  },
  {
    path: '/blackboard',
    name: 'Blackboard',
    component: BlackboardPage,
    meta: {
      title: 'DevopsFlow - Blackboard'
    }
  },
  // Add a catch-all route to redirect to home
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // Scroll to top when navigating to a new route
    if (savedPosition) {
      return savedPosition;
    } else {
      return { top: 0 };
    }
  }
});

// Update document title based on route meta
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'DevopsFlow';
  next();
});

export default router;
