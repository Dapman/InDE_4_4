/**
 * Date utility functions for relative time formatting.
 */

/**
 * Format a date as a relative time string (e.g., "2 hours ago", "3 days ago").
 * @param {string|Date} date - The date to format
 * @returns {string} Relative time string
 */
export function formatDistanceToNow(date) {
  if (!date) return '';

  const now = new Date();
  const then = new Date(date);
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  if (diffSec < 60) {
    return 'just now';
  }
  if (diffMin < 60) {
    return diffMin === 1 ? '1 minute ago' : `${diffMin} minutes ago`;
  }
  if (diffHour < 24) {
    return diffHour === 1 ? '1 hour ago' : `${diffHour} hours ago`;
  }
  if (diffDay < 7) {
    return diffDay === 1 ? '1 day ago' : `${diffDay} days ago`;
  }
  if (diffWeek < 4) {
    return diffWeek === 1 ? '1 week ago' : `${diffWeek} weeks ago`;
  }
  if (diffMonth < 12) {
    return diffMonth === 1 ? '1 month ago' : `${diffMonth} months ago`;
  }
  return diffYear === 1 ? '1 year ago' : `${diffYear} years ago`;
}

/**
 * Format a date as a short date string (e.g., "Jan 15").
 * @param {string|Date} date - The date to format
 * @returns {string} Short date string
 */
export function formatShortDate(date) {
  if (!date) return '';

  const d = new Date(date);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[d.getMonth()]} ${d.getDate()}`;
}

/**
 * Format a date as a full date string (e.g., "January 15, 2026").
 * @param {string|Date} date - The date to format
 * @returns {string} Full date string
 */
export function formatFullDate(date) {
  if (!date) return '';

  const d = new Date(date);
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

/**
 * Calculate days remaining until a target date.
 * @param {string|Date} targetDate - The target date
 * @returns {number} Number of days remaining (negative if past)
 */
export function daysUntil(targetDate) {
  if (!targetDate) return 0;

  const now = new Date();
  const target = new Date(targetDate);
  const diffMs = target - now;
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Format a duration in days as a readable string (e.g., "15 days", "2 weeks").
 * @param {number} days - Number of days
 * @returns {string} Formatted duration
 */
export function formatDuration(days) {
  if (days < 1) return 'less than a day';
  if (days === 1) return '1 day';
  if (days < 7) return `${days} days`;
  if (days < 14) return '1 week';
  if (days < 30) return `${Math.floor(days / 7)} weeks`;
  if (days < 60) return '1 month';
  if (days < 365) return `${Math.floor(days / 30)} months`;
  return `${Math.floor(days / 365)} years`;
}
