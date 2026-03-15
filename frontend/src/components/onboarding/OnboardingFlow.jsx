/*
 * OnboardingFlow - v4.3 Idea-first onboarding experience
 *
 * A 5-screen carousel that introduces InDE through the lens of the idea:
 *   Screen 1: "What's the idea you're working on?"
 *   Screen 2: "Your idea will get sharper as we work together"
 *   Screen 3: "Everything you build here stays with you"
 *   Screen 4: "You're in control of the pace"
 *   Screen 5: CTA - "Start developing my idea"
 *
 * All copy comes from Display Label Registry 'onboarding_depth_framing' category.
 * No module names, no methodology jargon, no progress percentages.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import {
  Lightbulb,
  TrendingUp,
  Shield,
  Clock,
  Rocket,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

// Onboarding screens with Display Label Registry copy
const ONBOARDING_SCREENS = [
  {
    key: 'screen_1',
    icon: Lightbulb,
    title: "What's the idea you're working on?",
    body: "Start by telling us what you're trying to build, solve, or change.",
    accent: 'inde',
  },
  {
    key: 'screen_2',
    icon: TrendingUp,
    title: 'Your idea will get sharper as we work together',
    body: "We'll help you understand it more deeply - who it helps, what could go wrong, and how to test it.",
    accent: 'inde',
  },
  {
    key: 'screen_3',
    icon: Shield,
    title: 'Everything you build here stays with you',
    body: 'Every question you answer and insight you capture makes your idea more defensible.',
    accent: 'inde',
  },
  {
    key: 'screen_4',
    icon: Clock,
    title: "You're in control of the pace",
    body: "Come back when you have something to think through. Your idea will be exactly where you left it.",
    accent: 'inde',
  },
  {
    key: 'screen_5',
    icon: Rocket,
    title: "Ready to dive in?",
    body: "Let's start developing your idea together.",
    cta: 'Start developing my idea',
    accent: 'inde',
  },
];

export function OnboardingFlow({ onComplete }) {
  const [currentScreen, setCurrentScreen] = useState(0);
  const navigate = useNavigate();

  const screen = ONBOARDING_SCREENS[currentScreen];
  const isLastScreen = currentScreen === ONBOARDING_SCREENS.length - 1;
  const isFirstScreen = currentScreen === 0;

  const handleNext = () => {
    if (isLastScreen) {
      onComplete?.();
      navigate('/pursuit/new');
    } else {
      setCurrentScreen((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (!isFirstScreen) {
      setCurrentScreen((prev) => prev - 1);
    }
  };

  const handleSkip = () => {
    onComplete?.();
    navigate('/');
  };

  const Icon = screen.icon;

  return (
    <div className="min-h-screen bg-surface-0 flex flex-col items-center justify-center px-4">
      {/* Progress dots */}
      <div className="absolute top-8 left-1/2 -translate-x-1/2 flex gap-2">
        {ONBOARDING_SCREENS.map((_, idx) => (
          <button
            key={idx}
            onClick={() => setCurrentScreen(idx)}
            className={cn(
              'w-2 h-2 rounded-full transition-colors',
              idx === currentScreen
                ? 'bg-inde-400'
                : 'bg-surface-4 hover:bg-surface-5'
            )}
          />
        ))}
      </div>

      {/* Skip button */}
      <button
        onClick={handleSkip}
        className="absolute top-8 right-8 text-caption text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        Skip
      </button>

      {/* Content card */}
      <div className="w-full max-w-lg">
        {/* Icon */}
        <div className="flex justify-center mb-8">
          <div className="w-20 h-20 rounded-2xl bg-inde-500/10 flex items-center justify-center">
            <Icon className="w-10 h-10 text-inde-400" />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-display-md text-center text-zinc-100 mb-4">
          {screen.title}
        </h1>

        {/* Body */}
        <p className="text-body-lg text-center text-zinc-400 mb-10 leading-relaxed">
          {screen.body}
        </p>

        {/* Navigation */}
        <div className="flex items-center justify-center gap-4">
          {!isFirstScreen && (
            <Button
              variant="ghost"
              onClick={handleBack}
              className="text-zinc-400 hover:text-zinc-200"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
          )}

          <Button
            onClick={handleNext}
            className="bg-inde-600 hover:bg-inde-700 text-white px-8"
          >
            {isLastScreen ? (
              <>
                {screen.cta}
                <Rocket className="w-4 h-4 ml-2" />
              </>
            ) : (
              <>
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Version */}
      <p className="absolute bottom-8 text-caption text-zinc-600">
        InDE v4.3.0
      </p>
    </div>
  );
}
