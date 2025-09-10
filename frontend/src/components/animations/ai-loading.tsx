import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Zap, BarChart3, Package, CheckCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { TypewriterText } from './success-animation';

interface AILoadingProps {
  show: boolean;
  currentStep: string;
  progress: number;
  steps: string[];
  completedSteps: string[];
}

export function AIProcessingLoader({
  show,
  currentStep,
  progress,
  steps,
  completedSteps
}: AILoadingProps) {
  if (!show) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      >
        <Card className="w-full max-w-md bg-white/95 dark:bg-gray-900/95 border shadow-xl">
          <CardContent className="p-6 space-y-6">
            {/* Header with brain icon */}
            <div className="flex items-center gap-3">
              <motion.div
                animate={{ 
                  scale: [1, 1.1, 1],
                  rotate: [0, 5, -5, 0]
                }}
                transition={{ 
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg"
              >
                <Brain className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </motion.div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                  AI Processing
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Generating optimized purchase order
                </p>
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Progress</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {Math.round(progress)}%
                </span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>

            {/* Current step with typewriter effect */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 border-2 border-blue-600 border-r-transparent rounded-full"
                />
                Current Step
              </div>
              
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className="ml-6 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800"
              >
                <TypewriterText
                  text={currentStep}
                  show={true}
                  speed={30}
                />
              </motion.div>
            </div>

            {/* Steps list */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Process Steps
              </h4>
              <div className="space-y-2">
                {steps.map((step, index) => {
                  const isCompleted = completedSteps.includes(step);
                  const isCurrent = step === currentStep;
                  
                  return (
                    <motion.div
                      key={step}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className={`flex items-center gap-2 text-sm p-2 rounded ${
                        isCurrent
                          ? 'bg-blue-50 dark:bg-blue-950/30 text-blue-900 dark:text-blue-100 border border-blue-200 dark:border-blue-800'
                          : isCompleted
                          ? 'text-green-700 dark:text-green-400'
                          : 'text-gray-500 dark:text-gray-400'
                      }`}
                    >
                      <div className="flex-shrink-0">
                        {isCompleted ? (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 500 }}
                          >
                            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                          </motion.div>
                        ) : isCurrent ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                            className="w-4 h-4 border-2 border-blue-600 border-r-transparent rounded-full"
                          />
                        ) : (
                          <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                        )}
                      </div>
                      <span className={isCompleted ? 'line-through' : ''}>{step}</span>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}

// Simple professional loading for buttons and inline elements
export function InlineLoader({ 
  show, 
  message, 
  size = 'sm' 
}: { 
  show: boolean; 
  message?: string; 
  size?: 'sm' | 'md' 
}) {
  if (!show) return null;

  const spinnerSize = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-2"
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        className={`${spinnerSize} border-2 border-current border-r-transparent rounded-full opacity-60`}
      />
      {message && (
        <motion.span
          initial={{ opacity: 0, x: -5 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="text-sm opacity-80"
        >
          {message}
        </motion.span>
      )}
    </motion.div>
  );
}

// Professional pulse animation for cards and important elements
export function ProfessionalPulse({ 
  children, 
  isActive = false,
  intensity = 'subtle'
}: { 
  children: React.ReactNode; 
  isActive?: boolean;
  intensity?: 'subtle' | 'medium' | 'strong';
}) {
  const pulseScale = {
    subtle: [1, 1.02, 1],
    medium: [1, 1.05, 1], 
    strong: [1, 1.08, 1]
  };

  return (
    <motion.div
      animate={isActive ? { scale: pulseScale[intensity] } : {}}
      transition={{
        duration: 2,
        repeat: isActive ? Infinity : 0,
        ease: "easeInOut"
      }}
      className={isActive ? 'relative' : ''}
    >
      {children}
      {isActive && (
        <motion.div
          animate={{ 
            opacity: [0, 0.1, 0],
            scale: [1, 1.1, 1]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute inset-0 bg-blue-500 rounded-lg pointer-events-none"
        />
      )}
    </motion.div>
  );
}