import React, { useEffect, useRef, useState } from 'react';
import { Box, BoxProps } from '@chakra-ui/react';

// Extending BoxProps directly
interface AnimatedSectionProps extends Omit<BoxProps, 'transition' | 'transform'> {
  children: React.ReactNode;
  direction?: 'up' | 'down' | 'left' | 'right';
  delay?: number;
  threshold?: number;
  duration?: number;
  distance?: number;
  parallax?: boolean;
  parallaxSpeed?: number;
}

/**
 * Компонент для анимации секций при прокрутке
 */
const AnimatedSection: React.FC<AnimatedSectionProps> = ({
  children,
  direction = 'up',
  delay = 0,
  threshold = 0.2,
  duration = 0.8,
  distance = 50,
  parallax = false,
  parallaxSpeed = 0.5,
  ...props
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [parallaxOffset, setParallaxOffset] = useState(0);
  const sectionRef = useRef<HTMLDivElement>(null);

  // Расчет начальной трансформации в зависимости от направления
  const getInitialTransform = () => {
    switch (direction) {
      case 'up':
        return `translateY(${distance}px)`;
      case 'down':
        return `translateY(-${distance}px)`;
      case 'left':
        return `translateX(${distance}px)`;
      case 'right':
        return `translateX(-${distance}px)`;
      default:
        return `translateY(${distance}px)`;
    }
  };

  // Добавление эффекта параллакса
  useEffect(() => {
    if (!parallax) return;

    let ticking = false;
    
    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (sectionRef.current) {
            const scrolled = window.pageYOffset;
            const rect = sectionRef.current.getBoundingClientRect();
            const sectionTop = rect.top + window.pageYOffset;
            const offset = (scrolled - sectionTop) * parallaxSpeed;
            setParallaxOffset(offset);
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [parallax, parallaxSpeed]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          setIsVisible(true);
          // Отключаем наблюдение после срабатывания
          if (sectionRef.current) {
            observer.unobserve(sectionRef.current);
          }
        }
      },
      {
        root: null, // viewport
        threshold: threshold, // при каком % видимости срабатывает
        rootMargin: '0px',
      }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => {
      if (sectionRef.current) {
        observer.unobserve(sectionRef.current);
      }
    };
  }, [threshold]);

  // Комбинированная трансформация включая параллакс, если он активен
  const getTransform = () => {
    const baseTransform = isVisible ? 'translate(0, 0)' : getInitialTransform();
    if (parallax && isVisible) {
      return `${baseTransform} translateY(${parallaxOffset}px)`;
    }
    return baseTransform;
  };

  return (
    <Box
      ref={sectionRef}
      opacity={isVisible ? 1 : 0}
      transform={getTransform()}
      transition={`opacity ${duration}s ease-out, transform ${duration}s ease-out`}
      transitionDelay={`${delay}s`}
      className={parallax ? 'parallax' : ''}
      {...props}
    >
      {children}
    </Box>
  );
};

export default AnimatedSection;