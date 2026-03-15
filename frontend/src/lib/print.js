/**
 * Print utilities for InDE
 * Provides functions to print artifacts, reports, and other content.
 */

/**
 * Open a print-friendly window with content and print it.
 * @param {Object} options - Print options
 * @param {string} options.title - Document title
 * @param {string} options.subtitle - Document subtitle (e.g., pursuit name)
 * @param {string} options.content - HTML content to print
 * @param {string} options.type - Content type (artifact, report, etc.)
 * @param {Object} options.metadata - Additional metadata (date, author, etc.)
 */
export function printContent({ title, subtitle, content, type = 'document', metadata = {} }) {
  // Create a new window for printing
  const printWindow = window.open('', '_blank', 'width=800,height=600');

  if (!printWindow) {
    alert('Please allow popups to print content.');
    return;
  }

  // Format date
  const printDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  // Build metadata section
  const metaItems = [];
  if (metadata.author) metaItems.push(`Author: ${metadata.author}`);
  if (metadata.version) metaItems.push(`Version: ${metadata.version}`);
  if (metadata.phase) metaItems.push(`Phase: ${metadata.phase}`);
  if (metadata.status) metaItems.push(`Status: ${metadata.status}`);
  metaItems.push(`Printed: ${printDate}`);

  // Build the print document
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} - InDE</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      font-size: 12pt;
      line-height: 1.6;
      color: #1a1a1a;
      padding: 40px;
      max-width: 800px;
      margin: 0 auto;
    }
    .header {
      border-bottom: 3px solid #6366f1;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }
    .logo {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .logo-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 14px;
    }
    .logo-text {
      font-size: 14pt;
      font-weight: 600;
      color: #6366f1;
    }
    h1 {
      font-size: 20pt;
      font-weight: 700;
      color: #1a1a1a;
      margin-bottom: 4px;
    }
    .subtitle {
      font-size: 11pt;
      color: #666;
    }
    .type-badge {
      display: inline-block;
      font-size: 9pt;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #6366f1;
      background: #eef2ff;
      padding: 2px 8px;
      border-radius: 4px;
      margin-top: 8px;
    }
    .content {
      margin-bottom: 32px;
    }
    .content h2 {
      font-size: 14pt;
      font-weight: 600;
      color: #1a1a1a;
      margin-top: 20px;
      margin-bottom: 10px;
      padding-bottom: 6px;
      border-bottom: 1px solid #e5e7eb;
    }
    .content h3 {
      font-size: 12pt;
      font-weight: 600;
      color: #374151;
      margin-top: 16px;
      margin-bottom: 8px;
    }
    .content p {
      margin: 10px 0;
      text-align: justify;
    }
    .content ul, .content ol {
      margin: 10px 0;
      padding-left: 24px;
    }
    .content li {
      margin: 6px 0;
    }
    .content pre {
      background: #f3f4f6;
      padding: 12px;
      border-radius: 6px;
      font-family: 'Courier New', monospace;
      font-size: 10pt;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    .content blockquote {
      border-left: 3px solid #6366f1;
      padding-left: 16px;
      margin: 16px 0;
      color: #4b5563;
      font-style: italic;
    }
    .content table {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
    }
    .content th, .content td {
      border: 1px solid #d1d5db;
      padding: 8px 12px;
      text-align: left;
    }
    .content th {
      background: #f9fafb;
      font-weight: 600;
    }
    .metadata {
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid #e5e7eb;
      font-size: 9pt;
      color: #6b7280;
    }
    .metadata-item {
      margin: 4px 0;
    }
    .footer {
      margin-top: 24px;
      text-align: center;
      font-size: 9pt;
      color: #9ca3af;
    }
    @media print {
      body {
        padding: 20px;
      }
      .no-print {
        display: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="logo">
      <div class="logo-icon">ID</div>
      <span class="logo-text">InDE</span>
    </div>
    <h1>${title}</h1>
    ${subtitle ? `<div class="subtitle">${subtitle}</div>` : ''}
    <span class="type-badge">${type}</span>
  </div>

  <div class="content">
    ${content}
  </div>

  <div class="metadata">
    ${metaItems.map(item => `<div class="metadata-item">${item}</div>`).join('')}
  </div>

  <div class="footer">
    Generated by InDE - Innovation Development Environment
  </div>

  <script>
    // Auto-print when loaded
    window.onload = function() {
      window.print();
    };
  </script>
</body>
</html>
  `;

  printWindow.document.write(html);
  printWindow.document.close();
}

/**
 * Print an artifact.
 * @param {Object} artifact - Artifact data
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printArtifact(artifact, pursuitTitle = '') {
  const title = artifact.name || artifact.title || 'Artifact';
  const type = artifact.artifact_type || artifact.type || 'artifact';

  // Format content based on type
  let content = '';
  const rawContent = artifact.content || artifact.data;

  if (typeof rawContent === 'string') {
    // Convert markdown-like content to HTML
    content = formatTextContent(rawContent);
  } else if (typeof rawContent === 'object') {
    content = formatObjectContent(rawContent);
  } else {
    content = '<p>No content available</p>';
  }

  printContent({
    title,
    subtitle: pursuitTitle,
    content,
    type: formatTypeName(type),
    metadata: {
      version: artifact.version ? `v${artifact.version}` : undefined,
      author: artifact.created_by,
    },
  });
}

/**
 * Format plain text content to HTML.
 */
function formatTextContent(text) {
  if (!text) return '';

  // Escape HTML
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Convert markdown-like formatting
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

  // Bold and italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Lists
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

  // Paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';

  // Clean up empty paragraphs
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<h[23]>)/g, '$1');
  html = html.replace(/(<\/h[23]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)<\/p>/g, '$1');

  return html;
}

/**
 * Format object content to HTML.
 */
function formatObjectContent(obj) {
  if (!obj) return '';

  let html = '';

  for (const [key, value] of Object.entries(obj)) {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    if (typeof value === 'object' && value !== null) {
      html += `<h3>${label}</h3>`;
      html += `<pre>${JSON.stringify(value, null, 2)}</pre>`;
    } else {
      html += `<h3>${label}</h3>`;
      html += `<p>${String(value)}</p>`;
    }
  }

  return html;
}

/**
 * Format type name for display.
 */
function formatTypeName(type) {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Print pursuit summary/report.
 * @param {Object} pursuit - Pursuit data
 * @param {Object} options - Additional options
 */
export function printPursuitSummary(pursuit, options = {}) {
  const { includeArtifacts = false, includeTimeline = false } = options;

  let content = '';

  // Basic info
  content += `<h2>Overview</h2>`;
  if (pursuit.description) {
    content += `<p>${pursuit.description}</p>`;
  }

  content += `<p><strong>Phase:</strong> ${pursuit.phase || 'Not set'}</p>`;
  content += `<p><strong>Status:</strong> ${pursuit.status || 'Active'}</p>`;
  content += `<p><strong>Methodology:</strong> ${pursuit.methodology || 'Not set'}</p>`;

  if (pursuit.health_score !== undefined) {
    content += `<p><strong>Health Score:</strong> ${pursuit.health_score}</p>`;
  }

  printContent({
    title: pursuit.title || 'Pursuit Summary',
    subtitle: 'Innovation Pursuit',
    content,
    type: 'Summary Report',
    metadata: {
      phase: pursuit.phase,
      status: pursuit.status,
    },
  });
}

/**
 * Print timeline data.
 * @param {Object} timelineData - Timeline data from API
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printTimeline(timelineData, pursuitTitle = '') {
  const data = timelineData || {};

  let content = '';

  // Overview section
  content += '<h2>Timeline Overview</h2>';
  content += '<table>';
  content += `<tr><td><strong>Started</strong></td><td>${data.started_at ? new Date(data.started_at).toLocaleDateString() : 'Not started'}</td></tr>`;
  content += `<tr><td><strong>Target End</strong></td><td>${data.target_end ? new Date(data.target_end).toLocaleDateString() : 'Not set'}</td></tr>`;
  content += `<tr><td><strong>Current Phase</strong></td><td>${formatTypeName(data.current_phase || data.phase || 'VISION')}</td></tr>`;
  content += '</table>';

  // Phase breakdown
  const phases = data.phases || [];
  if (phases.length > 0 || (typeof data.phases === 'object' && data.phases !== null)) {
    content += '<h2>Phase Breakdown</h2>';
    content += '<table><tr><th>Phase</th><th>Duration</th><th>Status</th></tr>';

    const phaseList = Array.isArray(phases) ? phases : Object.entries(data.phases).map(([name, d]) => ({ name, ...d }));
    phaseList.forEach(phase => {
      const phaseName = phase.name || phase.phase;
      const duration = phase.duration || phase.planned_days || phase.days || '-';
      const status = phase.status || 'pending';
      content += `<tr><td>${formatTypeName(phaseName)}</td><td>${duration} days</td><td>${formatTypeName(status)}</td></tr>`;
    });
    content += '</table>';
  }

  // Velocity section
  if (data.velocity) {
    content += '<h2>Velocity Metrics</h2>';
    content += '<table>';
    content += `<tr><td><strong>Current</strong></td><td>${data.velocity.current?.toFixed(1) || '--'} elem/week</td></tr>`;
    content += `<tr><td><strong>Expected</strong></td><td>${data.velocity.expected?.toFixed(1) || '--'} elem/week</td></tr>`;
    content += `<tr><td><strong>Ratio</strong></td><td>${data.velocity.ratio?.toFixed(2) || '--'}</td></tr>`;
    content += '</table>';
  }

  // Maturity section
  if (data.maturity) {
    content += '<h2>Maturity</h2>';
    content += '<table>';
    content += `<tr><td><strong>Score</strong></td><td>${data.maturity.score || '--'} / 100</td></tr>`;
    content += `<tr><td><strong>Level</strong></td><td>${formatTypeName(data.maturity.level || '--')}</td></tr>`;
    content += '</table>';
  }

  printContent({
    title: 'Timeline Report',
    subtitle: pursuitTitle,
    content,
    type: 'Timeline',
    metadata: {
      phase: data.current_phase || data.phase,
    },
  });
}

/**
 * Print team data.
 * @param {Object} teamData - Team data from API
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printTeam(teamData, pursuitTitle = '') {
  const data = teamData || {};
  const members = data.members || data.team || [];
  const activity = data.activity || [];
  const gaps = data.gaps || data.unaddressed_elements || [];

  let content = '';

  // Team roster
  content += '<h2>Team Roster</h2>';
  if (members.length > 0) {
    content += '<table><tr><th>Name</th><th>Role</th><th>Contributions</th></tr>';
    members.forEach(member => {
      content += `<tr><td>${member.name || member.email || 'Unknown'}</td><td>${formatTypeName(member.role || 'viewer')}</td><td>${member.contributions || 0}</td></tr>`;
    });
    content += '</table>';
  } else {
    content += '<p>Solo pursuit - no team members</p>';
  }

  // Contribution balance
  if (members.length > 1) {
    const totalContributions = members.reduce((sum, m) => sum + (m.contributions || 0), 0);
    content += '<h2>Contribution Balance</h2>';
    content += '<table><tr><th>Member</th><th>Percentage</th></tr>';
    members.forEach(member => {
      const percentage = totalContributions > 0 ? Math.round(((member.contributions || 0) / totalContributions) * 100) : 0;
      content += `<tr><td>${member.name || member.email || 'Unknown'}</td><td>${percentage}%</td></tr>`;
    });
    content += '</table>';
  }

  // Gaps
  if (gaps.length > 0) {
    content += '<h2>Unaddressed Elements</h2>';
    content += '<ul>';
    gaps.forEach(gap => {
      const element = gap.element || gap;
      content += `<li>${formatTypeName(element)}</li>`;
    });
    content += '</ul>';
  }

  printContent({
    title: 'Team Report',
    subtitle: pursuitTitle,
    content,
    type: 'Team',
    metadata: {},
  });
}

/**
 * Print health data.
 * @param {Object} healthData - Health data from API
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printHealth(healthData, pursuitTitle = '') {
  const data = healthData || {};
  const score = data.score ?? data.health_score ?? 50;
  const zone = data.zone || data.health_zone || 'CAUTION';
  const components = data.components || data.component_scores || {};
  const risks = data.risks || data.active_risks || [];

  let content = '';

  // Overall health
  content += '<h2>Overall Health</h2>';
  content += '<table>';
  content += `<tr><td><strong>Score</strong></td><td>${Math.round(score)} / 100</td></tr>`;
  content += `<tr><td><strong>Zone</strong></td><td>${formatTypeName(zone)}</td></tr>`;
  content += '</table>';

  // Component breakdown
  content += '<h2>Health Components</h2>';
  content += '<table><tr><th>Component</th><th>Score</th></tr>';
  const componentList = [
    ['Velocity', components.velocity ?? components.velocity_health ?? score],
    ['Completeness', components.completeness ?? components.element_coverage ?? score],
    ['Engagement', components.engagement ?? components.engagement_rhythm ?? score],
    ['Risk Balance', components.risk_balance ?? components.risk_posture ?? score],
    ['Time Health', components.time_health ?? components.phase_timing ?? score],
  ];
  componentList.forEach(([name, value]) => {
    content += `<tr><td>${name}</td><td>${Math.round(value)}</td></tr>`;
  });
  content += '</table>';

  // Active risks
  if (risks.length > 0) {
    content += '<h2>Active Risks</h2>';
    content += '<table><tr><th>Risk</th><th>Severity</th><th>Description</th></tr>';
    risks.forEach(risk => {
      content += `<tr><td>${formatTypeName(risk.type || risk.title || 'Unknown')}</td><td>${formatTypeName(risk.severity || 'medium')}</td><td>${risk.description || '-'}</td></tr>`;
    });
    content += '</table>';
  } else {
    content += '<h2>Active Risks</h2>';
    content += '<p>No active risks detected</p>';
  }

  printContent({
    title: 'Health Report',
    subtitle: pursuitTitle,
    content,
    type: 'Health',
    metadata: {
      status: zone,
    },
  });
}

/**
 * Print RVE (Risk Validation Engine) data.
 * @param {Object} rveData - RVE data from API
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printRVE(rveData, pursuitTitle = '') {
  const risks = rveData?.risks || [];

  let content = '';

  // Summary
  const highCount = risks.filter(r => r.severity?.toLowerCase() === 'high').length;
  const mediumCount = risks.filter(r => r.severity?.toLowerCase() === 'medium').length;
  const lowCount = risks.filter(r => r.severity?.toLowerCase() === 'low').length;

  content += '<h2>Risk Summary</h2>';
  content += '<table>';
  content += `<tr><td><strong>Total Risks</strong></td><td>${risks.length}</td></tr>`;
  content += `<tr><td><strong>High Priority</strong></td><td>${highCount}</td></tr>`;
  content += `<tr><td><strong>Medium Priority</strong></td><td>${mediumCount}</td></tr>`;
  content += `<tr><td><strong>Low Priority</strong></td><td>${lowCount}</td></tr>`;
  content += '</table>';

  // Risk details by severity
  ['high', 'medium', 'low'].forEach(severity => {
    const severityRisks = risks.filter(r => (r.severity?.toLowerCase() || 'medium') === severity);
    if (severityRisks.length > 0) {
      content += `<h2>${formatTypeName(severity)} Priority Risks</h2>`;
      content += '<table><tr><th>Risk</th><th>Status</th><th>Description</th></tr>';
      severityRisks.forEach(risk => {
        content += `<tr><td>${risk.title || formatTypeName(risk.type) || 'Unknown'}</td><td>${formatTypeName(risk.status || 'identified')}</td><td>${risk.description || '-'}</td></tr>`;
      });
      content += '</table>';
    }
  });

  if (risks.length === 0) {
    content += '<p>No risks identified</p>';
  }

  printContent({
    title: 'Risk Validation Report',
    subtitle: pursuitTitle,
    content,
    type: 'Risk Validation',
    metadata: {},
  });
}

/**
 * Print scaffolding data.
 * @param {Object} scaffoldData - Scaffolding data from API
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printScaffolding(scaffoldData, pursuitTitle = '') {
  const data = scaffoldData || {};

  // v4.0: Labels use innovator-facing goal vocabulary
  const categories = {
    vision: { label: 'Your Story', field: 'vision_elements' },
    fears: { label: 'Risks & Protections', field: 'fear_elements' },
    validation: { label: 'What You\'ve Tested', field: 'hypothesis_elements' },
    market: { label: 'Market & Technical Insights', field: 'important_elements' },
  };

  let content = '';
  let totalFilled = 0;
  let totalElements = 0;

  // Process each category
  Object.entries(categories).forEach(([catId, cat]) => {
    const elements = data[cat.field] || {};
    const elementList = Object.entries(elements);

    if (elementList.length > 0) {
      content += `<h2>${cat.label}</h2>`;
      content += '<table><tr><th>Element</th><th>Status</th><th>Value</th></tr>';

      elementList.forEach(([name, value]) => {
        totalElements++;
        const hasValue = value && (value.text || value.value);
        if (hasValue) totalFilled++;

        const displayValue = value?.text || value?.value || '';
        const truncatedValue = displayValue.length > 100 ? displayValue.substring(0, 100) + '...' : displayValue;

        content += `<tr><td>${formatTypeName(name)}</td><td>${hasValue ? '✓ Captured' : '○ Empty'}</td><td>${truncatedValue || '-'}</td></tr>`;
      });
      content += '</table>';
    }
  });

  // Summary at top
  const percentage = totalElements > 0 ? Math.round((totalFilled / totalElements) * 100) : 0;
  const summary = `<h2>Completion Summary</h2><table><tr><td><strong>Overall</strong></td><td>${percentage}% complete (${totalFilled} of ${totalElements} elements)</td></tr></table>`;
  content = summary + content;

  printContent({
    title: 'Innovation Scaffolding Report',
    subtitle: pursuitTitle,
    content,
    type: 'Scaffolding',
    metadata: {},
  });
}

/**
 * Print intelligence data.
 * @param {Object} intelligenceData - Intelligence data (patterns, cross-pollination, etc.)
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printIntelligence(intelligenceData, pursuitTitle = '') {
  const { patterns = [], crossPollination = [], velocity = {} } = intelligenceData || {};

  let content = '';

  // Learning velocity
  if (velocity.score !== undefined) {
    content += '<h2>Learning Velocity</h2>';
    content += '<table>';
    content += `<tr><td><strong>Score</strong></td><td>${Math.round(velocity.score)} / 100</td></tr>`;
    if (velocity.conversion_rate !== undefined) {
      content += `<tr><td><strong>Conversion Rate</strong></td><td>${Math.round(velocity.conversion_rate * 100)}%</td></tr>`;
    }
    if (velocity.org_average !== undefined) {
      content += `<tr><td><strong>Org Average</strong></td><td>${Math.round(velocity.org_average)}</td></tr>`;
    }
    content += '</table>';
  }

  // Pattern suggestions
  if (patterns.length > 0) {
    content += '<h2>Pattern Suggestions</h2>';
    patterns.slice(0, 10).forEach((pattern, i) => {
      content += `<h3>${i + 1}. ${pattern.summary || 'Pattern'} (${pattern.similarity || 0}% match)</h3>`;
      if (pattern.key_insight) {
        content += `<blockquote>${pattern.key_insight}</blockquote>`;
      }
      if (pattern.detail) {
        content += `<p>${pattern.detail}</p>`;
      }
    });
  } else {
    content += '<h2>Pattern Suggestions</h2>';
    content += '<p>No pattern suggestions available</p>';
  }

  // Cross-pollination
  if (crossPollination.length > 0) {
    content += '<h2>Cross-Pollination Insights</h2>';
    crossPollination.slice(0, 5).forEach((insight, i) => {
      content += `<h3>${i + 1}. From: ${insight.source_domain || 'Unknown Domain'}</h3>`;
      content += `<p>${insight.bridge_description || ''}</p>`;
      if (insight.transfer_probability) {
        content += `<p><em>Transfer probability: ${Math.round(insight.transfer_probability * 100)}%</em></p>`;
      }
    });
  }

  printContent({
    title: 'Intelligence Report',
    subtitle: pursuitTitle,
    content,
    type: 'Intelligence',
    metadata: {},
  });
}

/**
 * Print convergence data.
 * @param {Object} convergenceData - Convergence data from API
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printConvergence(convergenceData, pursuitTitle = '') {
  const data = convergenceData || {};
  const phase = data.phase || data.convergence_phase || 'EXPLORING';
  const criteria = data.criteria || data.transition_criteria || [];
  const outcomes = data.outcomes || data.captured_outcomes || [];

  let content = '';

  // Phase status
  content += '<h2>Convergence Status</h2>';
  content += '<table>';
  content += `<tr><td><strong>Current Phase</strong></td><td>${formatTypeName(phase)}</td></tr>`;

  const satisfiedCount = criteria.filter(c => c.satisfied || c.met || c.complete).length;
  content += `<tr><td><strong>Criteria Met</strong></td><td>${satisfiedCount} of ${criteria.length}</td></tr>`;
  content += '</table>';

  // Transition criteria
  if (criteria.length > 0) {
    content += '<h2>Transition Criteria</h2>';
    content += '<table><tr><th>Criterion</th><th>Status</th></tr>';
    criteria.forEach(criterion => {
      const satisfied = criterion.satisfied || criterion.met || criterion.complete;
      content += `<tr><td>${criterion.description || formatTypeName(criterion.name || criterion.type)}</td><td>${satisfied ? '✓ Met' : '○ Pending'}</td></tr>`;
    });
    content += '</table>';
  }

  // Captured outcomes
  if (outcomes.length > 0) {
    content += '<h2>Captured Outcomes</h2>';
    outcomes.forEach((outcome, i) => {
      content += `<h3>${i + 1}. ${formatTypeName(outcome.phase || 'Outcome')}</h3>`;
      content += `<blockquote>${outcome.content || outcome.decision || ''}</blockquote>`;
    });
  }

  printContent({
    title: 'Convergence Report',
    subtitle: pursuitTitle,
    content,
    type: 'Convergence',
    metadata: {
      phase: phase,
    },
  });
}

/**
 * Print contribution data.
 * @param {Object} contributionData - Contribution data
 * @param {string} pursuitTitle - Title of the pursuit
 */
export function printContributions(contributionData, pursuitTitle = '') {
  const { drafts = [], history = [] } = contributionData || {};

  const packageLabels = {
    temporal_benchmark: 'Timing & Velocity',
    pattern_contribution: 'Innovation Pattern',
    risk_intelligence: 'Risk Methodology',
    effectiveness: 'Effectiveness Metrics',
    retrospective_wisdom: 'Retrospective Learning',
  };

  let content = '';

  // Pending contributions
  content += '<h2>Pending Contributions</h2>';
  if (drafts.length > 0) {
    content += '<table><tr><th>Type</th><th>Status</th><th>Date</th></tr>';
    drafts.forEach(contrib => {
      const typeLabel = packageLabels[contrib.package_type] || contrib.package_type || 'Contribution';
      content += `<tr><td>${typeLabel}</td><td>${formatTypeName(contrib.status || 'DRAFT')}</td><td>${contrib.created_at ? new Date(contrib.created_at).toLocaleDateString() : '-'}</td></tr>`;
    });
    content += '</table>';
  } else {
    content += '<p>No pending contributions</p>';
  }

  // Contribution history
  if (history.length > 0) {
    content += '<h2>Contribution History</h2>';
    content += '<table><tr><th>Type</th><th>Status</th><th>Date</th></tr>';
    history.slice(0, 20).forEach(contrib => {
      const typeLabel = packageLabels[contrib.package_type] || contrib.package_type || 'Contribution';
      content += `<tr><td>${typeLabel}</td><td>${formatTypeName(contrib.status || 'Unknown')}</td><td>${contrib.updated_at ? new Date(contrib.updated_at).toLocaleDateString() : '-'}</td></tr>`;
    });
    content += '</table>';
  }

  printContent({
    title: 'Contributions Report',
    subtitle: pursuitTitle,
    content,
    type: 'Contributions',
    metadata: {},
  });
}

export default {
  printContent,
  printArtifact,
  printPursuitSummary,
  printTimeline,
  printTeam,
  printHealth,
  printRVE,
  printScaffolding,
  printIntelligence,
  printConvergence,
  printContributions,
};
