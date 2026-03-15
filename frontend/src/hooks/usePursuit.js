import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usePursuitStore } from '../stores/pursuitStore';
import { pursuitsApi } from '../api/pursuits';

/**
 * Hook for managing pursuit data and state.
 */
export function usePursuit(pursuitId) {
  const queryClient = useQueryClient();
  const { cachePursuit, setActivePursuit, getActivePursuit } = usePursuitStore();

  // Fetch pursuit data
  const {
    data: pursuit,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['pursuit', pursuitId],
    queryFn: async () => {
      const response = await pursuitsApi.get(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000, // 30 seconds
  });

  // Cache pursuit when loaded
  useEffect(() => {
    if (pursuit) {
      cachePursuit(pursuitId, pursuit);
    }
  }, [pursuit, pursuitId, cachePursuit]);

  // Set as active when viewing
  useEffect(() => {
    if (pursuitId) {
      setActivePursuit(pursuitId);
    }
    return () => {
      // Don't clear on unmount - keep last active
    };
  }, [pursuitId, setActivePursuit]);

  // Mutations
  const updateMutation = useMutation({
    mutationFn: (data) => pursuitsApi.update(pursuitId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['pursuit', pursuitId]);
      queryClient.invalidateQueries(['pursuits']);
    },
  });

  const transitionStateMutation = useMutation({
    mutationFn: ({ newState, rationale }) => pursuitsApi.transitionState(pursuitId, newState, rationale),
    onSuccess: () => {
      queryClient.invalidateQueries(['pursuit', pursuitId]);
      queryClient.invalidateQueries(['pursuits']);
    },
  });

  const transitionPhaseMutation = useMutation({
    mutationFn: ({ targetPhase, rationale }) => pursuitsApi.transitionPhase(pursuitId, targetPhase, rationale),
    onSuccess: () => {
      queryClient.invalidateQueries(['pursuit', pursuitId]);
    },
  });

  return {
    pursuit,
    isLoading,
    error,
    refetch,
    update: updateMutation.mutateAsync,
    transitionState: transitionStateMutation.mutateAsync,
    transitionPhase: transitionPhaseMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
  };
}

/**
 * Hook for listing all pursuits.
 */
export function usePursuitList() {
  const { setPursuitList } = usePursuitStore();

  const { data: pursuits = [], isLoading, error, refetch } = useQuery({
    queryKey: ['pursuits'],
    queryFn: async () => {
      const response = await pursuitsApi.list();
      return response.data;
    },
    staleTime: 30000,
  });

  // Sync to store
  useEffect(() => {
    if (pursuits.length > 0) {
      setPursuitList(pursuits);
    }
  }, [pursuits, setPursuitList]);

  return {
    pursuits,
    activePursuits: pursuits.filter((p) => p.state === 'ACTIVE'),
    archivedPursuits: pursuits.filter((p) => p.state === 'ARCHIVED'),
    isLoading,
    error,
    refetch,
  };
}

/**
 * Hook for creating a new pursuit.
 */
export function useCreatePursuit() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => pursuitsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['pursuits']);
    },
  });
}
