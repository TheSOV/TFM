/**
 * Utility functions for formatting data
 */

/**
 * Format a date object into a readable string
 * @param {Date|string|number} date - Date to format
 * @returns {string} Formatted date string
 */
export function formatDate(date) {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });
}

/**
 * Format bytes to human-readable string
 * @param {number} bytes - Number of bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted string
 */
export function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

/**
 * Truncate a string to a specified length, adding an ellipsis if truncated
 * @param {string} str - String to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated string
 */
export function truncateString(str, maxLength = 100) {
  if (typeof str !== 'string') return '';
  if (str.length <= maxLength) return str;
  
  return `${str.substring(0, maxLength)}...`;
}

/**
 * Format a duration in milliseconds to a human-readable string
 * @param {number} ms - Duration in milliseconds
 * @returns {string} Formatted duration
 */
export function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/**
 * Convert an object to a pretty-printed JSON string
 * @param {Object} obj - Object to format
 * @param {number} indent - Number of spaces for indentation
 * @returns {string} Formatted JSON string
 */
export function toPrettyJson(obj, indent = 2) {
  try {
    return JSON.stringify(obj, null, indent);
  } catch (e) {
    console.error('Error formatting JSON:', e);
    return String(obj);
  }
}

/**
 * Format a string with placeholders using an object of replacements
 * Example: formatString('Hello {name}!', { name: 'World' }) -> 'Hello World!'
 * @param {string} str - String with {placeholders}
 * @param {Object} replacements - Object with replacement values
 * @returns {string} Formatted string
 */
export function formatString(str, replacements = {}) {
  return str.replace(/\{([^}]+)\}/g, (match, key) => {
    return replacements[key] !== undefined ? replacements[key] : match;
  });
}
