/**
 * Application-wide constants.
 */

// API configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// App info
export const APP_NAME = 'InDE';
export const APP_VERSION = '3.7.4';
export const APP_TAGLINE = 'Innovation Development Environment';

// Innovation phases
export const INNOVATION_PHASES = {
  VISION: 'VISION',
  PITCH: 'PITCH',
  DE_RISK: 'DE_RISK',
  BUILD: 'BUILD',
  DEPLOY: 'DEPLOY',
};

// Health zones
export const HEALTH_ZONES = {
  THRIVING: 'THRIVING',
  HEALTHY: 'HEALTHY',
  CAUTION: 'CAUTION',
  AT_RISK: 'AT_RISK',
  CRITICAL: 'CRITICAL',
};

// Confidence tiers
export const CONFIDENCE_TIERS = {
  HIGH: 'HIGH',
  MODERATE: 'MODERATE',
  LOW: 'LOW',
  INSUFFICIENT: 'INSUFFICIENT',
};

// Coaching modes
export const COACHING_MODES = {
  COACHING: 'coaching',
  VISION: 'vision',
  FEAR: 'fear',
  RETROSPECTIVE: 'retrospective',
  NON_DIRECTIVE: 'non_directive',
  EMS_REVIEW: 'ems_review',
};

// Pursuit states
export const PURSUIT_STATES = {
  ACTIVE: 'ACTIVE',
  PAUSED: 'PAUSED',
  COMPLETED: 'COMPLETED',
  TERMINATED: 'TERMINATED',
  ARCHIVED: 'ARCHIVED',
};

// Keyboard shortcuts
export const SHORTCUTS = {
  COMMAND_PALETTE: { key: 'k', meta: true },
  TOGGLE_LEFT_SIDEBAR: { key: '\\', meta: true },
  TOGGLE_RIGHT_SIDEBAR: { key: ']', meta: true },
  NEW_PURSUIT: { key: 'n', meta: true, shift: true },
  SEARCH: { key: '/', meta: false },
};

// Default panel widths
export const PANEL_WIDTHS = {
  LEFT_SIDEBAR_COLLAPSED: 56,
  LEFT_SIDEBAR_EXPANDED: 256,
  RIGHT_SIDEBAR: 320,
  TOPBAR_HEIGHT: 56,
  STATUSBAR_HEIGHT: 28,
};

// Breakpoints (must match Tailwind config)
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  '2XL': 1536,
};
