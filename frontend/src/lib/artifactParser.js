/**
 * Artifact Parser
 *
 * Parses coaching responses for artifact markers and extracts structured data.
 * Marker format: [ARTIFACT:type]...content...[/ARTIFACT]
 */

// Valid artifact types for rendering
const VALID_ARTIFACT_TYPES = [
  // Text-based
  'vision', 'vision_statement', 'elevator_pitch', 'value_proposition',
  'hypothesis', 'fear_register', 'summary',
  // Charts
  'bar_chart', 'line_chart', 'pie_chart', 'strategy_canvas',
  // Positioning/Maps
  'positioning_map', 'perceptual_map',
  // Matrices
  'swot', '2x2_matrix', 'comparison_matrix', 'matrix',
  // Forms
  'survey', 'questionnaire', 'form',
  // Generic
  'artifact', 'document',
];

// Regex to match artifact markers
const ARTIFACT_REGEX = /\[ARTIFACT:(\w+)\]([\s\S]*?)\[\/ARTIFACT\]/g;

/**
 * Parse artifact content from a coach message
 * @param {string} content - The raw message content
 * @returns {{ segments: Array, artifacts: Array }}
 */
export function parseArtifactContent(content) {
  if (!content || typeof content !== 'string') {
    return { segments: [{ type: 'text', content: '' }], artifacts: [] };
  }

  const segments = [];
  const artifacts = [];
  let lastIndex = 0;

  // Reset regex state
  ARTIFACT_REGEX.lastIndex = 0;

  let match;
  while ((match = ARTIFACT_REGEX.exec(content)) !== null) {
    const [fullMatch, artifactType, artifactContent] = match;
    const startIndex = match.index;

    // Add text before this artifact
    if (startIndex > lastIndex) {
      const textContent = content.substring(lastIndex, startIndex).trim();
      if (textContent) {
        segments.push({ type: 'text', content: textContent });
      }
    }

    // Parse the artifact
    const artifact = parseArtifact(artifactType, artifactContent.trim(), startIndex);
    artifacts.push(artifact);
    segments.push({ type: 'artifact', artifact });

    lastIndex = startIndex + fullMatch.length;
  }

  // Add remaining text after last artifact
  if (lastIndex < content.length) {
    const textContent = content.substring(lastIndex).trim();
    if (textContent) {
      segments.push({ type: 'text', content: textContent });
    }
  }

  // If no artifacts found, return entire content as text
  if (segments.length === 0) {
    segments.push({ type: 'text', content });
  }

  return { segments, artifacts };
}

/**
 * Parse a single artifact from its content
 * @param {string} type - Artifact type from marker
 * @param {string} rawContent - Raw content between markers
 * @param {number} startIndex - Position in original content
 * @returns {Object} Parsed artifact object
 */
function parseArtifact(type, rawContent, startIndex) {
  const artifact = {
    id: generateArtifactId(),
    type: type.toLowerCase(),
    title: '',
    content: rawContent,
    data: null,
    startIndex,
    createdAt: new Date().toISOString(),
  };

  // Try to parse as JSON
  try {
    const jsonData = JSON.parse(rawContent);
    artifact.data = jsonData;
    artifact.title = jsonData.title || generateTitle(type);
    artifact.content = jsonData.content || rawContent;
  } catch {
    // Not JSON, treat as raw content
    artifact.title = generateTitle(type);

    // Try to extract title from first line if it looks like a heading
    const lines = rawContent.split('\n');
    if (lines.length > 0) {
      const firstLine = lines[0].trim();
      // Check for markdown heading or title-like first line
      if (firstLine.startsWith('#')) {
        artifact.title = firstLine.replace(/^#+\s*/, '');
      } else if (firstLine.length < 100 && !firstLine.includes('.')) {
        artifact.title = firstLine;
      }
    }
  }

  return artifact;
}

/**
 * Generate a title from artifact type
 * @param {string} type - Artifact type
 * @returns {string} Human-readable title
 */
// v4.0: Titles use innovator-facing goal vocabulary
function generateTitle(type) {
  const titles = {
    vision: 'Your Innovation Story',
    vision_statement: 'Your Innovation Story',
    elevator_pitch: 'Your Pitch',
    value_proposition: 'Value Proposition',
    hypothesis: 'Key Assumption',
    fear_register: 'Risks & Protections',
    summary: 'Summary',
    bar_chart: 'Bar Chart',
    line_chart: 'Line Chart',
    pie_chart: 'Pie Chart',
    strategy_canvas: 'Strategy Canvas',
    positioning_map: 'Positioning Map',
    perceptual_map: 'Perceptual Map',
    swot: 'SWOT Analysis',
    '2x2_matrix': '2x2 Matrix',
    comparison_matrix: 'Comparison Matrix',
    matrix: 'Matrix',
    survey: 'Survey',
    questionnaire: 'Questionnaire',
    form: 'Form',
    artifact: 'Artifact',
    document: 'Document',
  };

  return titles[type.toLowerCase()] || type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Generate a unique artifact ID
 * @returns {string} UUID-like ID
 */
function generateArtifactId() {
  return `art_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Check if a type is a valid artifact type
 * @param {string} type - Type to check
 * @returns {boolean}
 */
export function isValidArtifactType(type) {
  return VALID_ARTIFACT_TYPES.includes(type?.toLowerCase());
}

/**
 * Get the renderer category for an artifact type
 * @param {string} type - Artifact type
 * @returns {string} Renderer category: 'text' | 'chart' | 'positioning' | 'matrix' | 'form'
 */
export function getRendererCategory(type) {
  const typeLC = type?.toLowerCase();

  // Chart types
  if (['bar_chart', 'line_chart', 'pie_chart', 'strategy_canvas'].includes(typeLC)) {
    return 'chart';
  }

  // Positioning/map types
  if (['positioning_map', 'perceptual_map'].includes(typeLC)) {
    return 'positioning';
  }

  // Matrix types
  if (['swot', '2x2_matrix', 'comparison_matrix', 'matrix'].includes(typeLC)) {
    return 'matrix';
  }

  // Form types
  if (['survey', 'questionnaire', 'form'].includes(typeLC)) {
    return 'form';
  }

  // Default to text
  return 'text';
}

/**
 * Get icon name for an artifact type (for Lucide icons)
 * @param {string} type - Artifact type
 * @returns {string} Icon name
 */
export function getArtifactIcon(type) {
  const typeLC = type?.toLowerCase();

  const icons = {
    vision: 'Lightbulb',
    vision_statement: 'Lightbulb',
    elevator_pitch: 'Megaphone',
    value_proposition: 'Target',
    hypothesis: 'FlaskConical',
    fear_register: 'AlertTriangle',
    summary: 'FileText',
    bar_chart: 'BarChart3',
    line_chart: 'LineChart',
    pie_chart: 'PieChart',
    strategy_canvas: 'BarChart2',
    positioning_map: 'Grid3X3',
    perceptual_map: 'Grid3X3',
    swot: 'Table2',
    '2x2_matrix': 'Grid2X2',
    comparison_matrix: 'Table',
    matrix: 'Table2',
    survey: 'ClipboardList',
    questionnaire: 'ClipboardList',
    form: 'FileInput',
    artifact: 'File',
    document: 'FileText',
  };

  return icons[typeLC] || 'File';
}

export default {
  parseArtifactContent,
  isValidArtifactType,
  getRendererCategory,
  getArtifactIcon,
};
