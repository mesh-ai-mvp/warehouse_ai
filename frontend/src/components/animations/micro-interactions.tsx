import React, { ReactNode, useRef, MouseEvent, useEffect } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';

// Professional hover effect for cards and interactive elements
export function HoverCard({ 
  children, 
  className = "",
  disabled = false
}: { 
  children: ReactNode; 
  className?: string;
  disabled?: boolean;
}) {
  if (disabled) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      whileHover={{ 
        y: -2,
        transition: { duration: 0.2, ease: "easeOut" }
      }}
      whileTap={{ 
        scale: 0.98,
        transition: { duration: 0.1 }
      }}
      style={{
        boxShadow: "0 1px 3px rgba(0, 0, 0, 0.1)"
      }}
      initial={false}
      animate={{
        boxShadow: [
          "0 1px 3px rgba(0, 0, 0, 0.1)",
          "0 4px 12px rgba(0, 0, 0, 0.15)",
          "0 1px 3px rgba(0, 0, 0, 0.1)"
        ]
      }}
      transition={{
        duration: 0.3,
        ease: "easeInOut"
      }}
    >
      {children}
    </motion.div>
  );
}

// Magnetic effect for important buttons
export function MagneticButton({ 
  children, 
  strength = 0.3,
  className = ""
}: { 
  children: ReactNode; 
  strength?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  
  const xSpring = useSpring(x, { stiffness: 300, damping: 30 });
  const ySpring = useSpring(y, { stiffness: 300, damping: 30 });

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    
    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const deltaX = (e.clientX - centerX) * strength;
    const deltaY = (e.clientY - centerY) * strength;
    
    x.set(deltaX);
    y.set(deltaY);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      ref={ref}
      className={className}
      style={{ x: xSpring, y: ySpring }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

// Professional button with loading state
export function AnimatedButton({
  children,
  isLoading = false,
  success = false,
  disabled = false,
  onClick,
  className = "",
  ...props
}: {
  children: ReactNode;
  isLoading?: boolean;
  success?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
  [key: string]: any;
}) {
  return (
    <motion.button
      className={`${className} relative overflow-hidden`}
      onClick={onClick}
      disabled={disabled || isLoading}
      whileHover={!disabled && !isLoading ? { scale: 1.02 } : {}}
      whileTap={!disabled && !isLoading ? { scale: 0.98 } : {}}
      transition={{ duration: 0.1, ease: "easeOut" }}
      {...props}
    >
      <motion.div
        animate={{
          opacity: isLoading ? 0 : 1,
          y: isLoading ? -20 : 0
        }}
        transition={{ duration: 0.2 }}
      >
        {children}
      </motion.div>

      {isLoading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="absolute inset-0 flex items-center justify-center"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="w-4 h-4 border-2 border-current border-r-transparent rounded-full"
          />
        </motion.div>
      )}

      {success && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 500 }}
          className="absolute inset-0 flex items-center justify-center bg-green-500 text-white rounded-md"
        >
          ✓
        </motion.div>
      )}
    </motion.button>
  );
}

// Smooth number transitions
export function AnimatedNumber({ 
  value, 
  duration = 1,
  format = (n: number) => n.toLocaleString(),
  className = ""
}: { 
  value: number; 
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const motionValue = useMotionValue(0);
  const displayValue = useTransform(motionValue, (v) => format(Math.round(v)));

  // Update the motion value when the target value changes
  useEffect(() => {
    const controls = motionValue.start(value, { duration, ease: "easeOut" });
    return controls.stop;
  }, [value, duration, motionValue]);

  return (
    <motion.span className={className}>
      {displayValue}
    </motion.span>
  );
}

// Staggered list animations
export function StaggeredList({ 
  children, 
  stagger = 0.1,
  className = ""
}: { 
  children: ReactNode[]; 
  stagger?: number;
  className?: string;
}) {
  const childrenArray = React.Children.toArray(children);

  return (
    <div className={className}>
      {childrenArray.map((child, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ 
            delay: index * stagger,
            duration: 0.4,
            ease: "easeOut"
          }}
        >
          {child}
        </motion.div>
      ))}
    </div>
  );
}

// Page transition wrapper
export function PageTransition({ 
  children,
  className = ""
}: { 
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Subtle focus ring animation
export function FocusRing({ 
  children, 
  show = false 
}: { 
  children: ReactNode; 
  show?: boolean 
}) {
  return (
    <motion.div
      className="relative"
      animate={show ? {
        boxShadow: [
          "0 0 0 0 rgba(59, 130, 246, 0)",
          "0 0 0 3px rgba(59, 130, 246, 0.1)",
          "0 0 0 3px rgba(59, 130, 246, 0)"
        ]
      } : {}}
      transition={{ duration: 1.5, ease: "easeInOut" }}
    >
      {children}
    </motion.div>
  );
}