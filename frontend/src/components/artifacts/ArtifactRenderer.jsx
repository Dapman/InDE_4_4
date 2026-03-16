/**
 * ArtifactRenderer - Routes to appropriate type-specific renderer
 *
 * Determines which renderer to use based on artifact type and
 * renders the artifact content appropriately.
 */

import { getRendererCategory } from '../../lib/artifactParser';
import { TextArtifactRenderer } from './renderers/TextArtifactRenderer';
import { ChartRenderer } from './renderers/ChartRenderer';
import { PositioningMapRenderer } from './renderers/PositioningMapRenderer';
import { MatrixRenderer } from './renderers/MatrixRenderer';
import { FormRenderer } from './renderers/FormRenderer';

// Renderer mapping by category
const RENDERERS = {
  text: TextArtifactRenderer,
  chart: ChartRenderer,
  positioning: PositioningMapRenderer,
  matrix: MatrixRenderer,
  form: FormRenderer,
};

export function ArtifactRenderer({ artifact }) {
  if (!artifact) {
    return (
      <div className="text-center text-zinc-500 py-8">
        No artifact data available
      </div>
    );
  }

  const category = getRendererCategory(artifact.type);
  const Renderer = RENDERERS[category] || TextArtifactRenderer;

  return <Renderer artifact={artifact} />;
}

export default ArtifactRenderer;
