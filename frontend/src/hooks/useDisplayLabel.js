import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../api/system';

/**
 * Fetch and cache all Display Labels.
 * Labels are fetched once and cached for the session lifetime.
 */
export function useDisplayLabels() {
  return useQuery({
    queryKey: ['display-labels'],
    queryFn: () => systemApi.getDisplayLabels(),
    staleTime: Infinity, // Labels don't change during a session
    gcTime: Infinity,
    retry: 2,
  });
}

/**
 * Get a specific Display Label value.
 * Returns { label, icon, description } or fallback.
 */
export function useDisplayLabel(category, value) {
  const { data: labels } = useDisplayLabels();

  if (!labels || !labels[category] || !labels[category][value]) {
    // Fallback: humanize the raw value
    return {
      label: value?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || '',
      icon: null,
      description: null,
    };
  }

  return labels[category][value];
}

/**
 * Get all labels for a category.
 */
export function useDisplayLabelCategory(category) {
  const { data: labels } = useDisplayLabels();
  return labels?.[category] || {};
}
