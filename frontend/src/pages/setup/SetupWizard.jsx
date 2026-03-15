/**
 * InDE First-Run Setup Wizard
 *
 * A 6-step guided setup flow for new deployments:
 * 1. License Activation
 * 2. Organization Setup
 * 3. Admin Account Creation
 * 4. API Key Configuration
 * 5. System Verification
 * 6. Setup Complete
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

import LicenseActivation from './steps/LicenseActivation';
import OrganizationSetup from './steps/OrganizationSetup';
import AdminAccount from './steps/AdminAccount';
import ApiKeyConfig from './steps/ApiKeyConfig';
import SystemCheck from './steps/SystemCheck';
import SetupComplete from './steps/SetupComplete';

const STEPS = [
  { id: 'license', title: 'License Activation', component: LicenseActivation },
  { id: 'organization', title: 'Organization Setup', component: OrganizationSetup },
  { id: 'admin', title: 'Admin Account', component: AdminAccount },
  { id: 'apikey', title: 'API Key Configuration', component: ApiKeyConfig },
  { id: 'verify', title: 'System Verification', component: SystemCheck },
  { id: 'complete', title: 'Setup Complete', component: SetupComplete },
];

export default function SetupWizard() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [wizardData, setWizardData] = useState({
    license: null,
    organization: null,
    admin: null,
    apiKey: null,
    verification: null,
  });
  const [isValidating, setIsValidating] = useState(false);

  // Check if setup is already complete
  useEffect(() => {
    checkFirstRun();
  }, []);

  const checkFirstRun = async () => {
    try {
      const response = await fetch('/api/system/first-run');
      const data = await response.json();
      if (!data.setup_required) {
        // Setup already complete, redirect to login
        navigate('/login');
      }
    } catch (error) {
      console.error('Error checking first-run status:', error);
    }
  };

  const updateWizardData = (key, value) => {
    setWizardData((prev) => ({ ...prev, [key]: value }));
  };

  const canProceed = () => {
    switch (STEPS[currentStep].id) {
      case 'license':
        return wizardData.license?.valid;
      case 'organization':
        return wizardData.organization?.id;
      case 'admin':
        return wizardData.admin?.created;
      case 'apikey':
        return wizardData.apiKey?.valid;
      case 'verify':
        return wizardData.verification?.allPassed;
      case 'complete':
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < STEPS.length - 1 && canProceed()) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleComplete = async () => {
    try {
      // Mark setup as complete
      await fetch('/api/system/setup-complete', { method: 'POST' });
      // Navigate to login
      navigate('/login');
    } catch (error) {
      console.error('Error completing setup:', error);
    }
  };

  const CurrentStepComponent = STEPS[currentStep].component;

  return (
    <div className="min-h-screen bg-gradient-to-br from-inde-900 via-inde-800 to-inde-950 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            InDE Setup
          </h1>
          <p className="text-inde-300">
            Innovation Development Environment
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            {STEPS.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    ${index < currentStep
                      ? 'bg-green-500 text-white'
                      : index === currentStep
                      ? 'bg-inde-500 text-white'
                      : 'bg-inde-700 text-inde-400'
                    }
                  `}
                >
                  {index < currentStep ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    index + 1
                  )}
                </div>
                {index < STEPS.length - 1 && (
                  <div
                    className={`w-12 h-0.5 mx-2 ${
                      index < currentStep ? 'bg-green-500' : 'bg-inde-700'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <p className="text-center text-inde-400 mt-4 text-sm">
            Step {currentStep + 1} of {STEPS.length}: {STEPS[currentStep].title}
          </p>
        </div>

        {/* Step Content */}
        <div className="bg-inde-800/50 backdrop-blur rounded-xl border border-inde-700 p-6 min-h-[400px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              <CurrentStepComponent
                data={wizardData}
                updateData={updateWizardData}
                onValidating={setIsValidating}
              />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <div className="flex justify-between mt-6">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className={`
              px-4 py-2 rounded-lg flex items-center gap-2
              ${currentStep === 0
                ? 'bg-inde-700/50 text-inde-500 cursor-not-allowed'
                : 'bg-inde-700 text-white hover:bg-inde-600'
              }
            `}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>

          {currentStep < STEPS.length - 1 ? (
            <button
              onClick={handleNext}
              disabled={!canProceed() || isValidating}
              className={`
                px-4 py-2 rounded-lg flex items-center gap-2
                ${!canProceed() || isValidating
                  ? 'bg-inde-700/50 text-inde-500 cursor-not-allowed'
                  : 'bg-inde-500 text-white hover:bg-inde-400'
                }
              `}
            >
              {isValidating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Validating...
                </>
              ) : (
                <>
                  Continue
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleComplete}
              className="px-6 py-2 rounded-lg bg-green-600 text-white hover:bg-green-500 flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Launch InDE
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
