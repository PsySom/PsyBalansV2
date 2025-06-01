import React, { useState, useEffect, useRef } from 'react';
import { Text, TextProps } from '@chakra-ui/react';

interface CountUpProps extends TextProps {
  start?: number;
  end: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  separator?: string;
  decimals?: number;
  decimal?: string;
}

/**
 * Компонент для анимированного отображения числа с эффектом счета
 */
const CountUp: React.FC<CountUpProps> = ({
  start = 0,
  end,
  duration = 2000,
  prefix = '',
  suffix = '',
  separator = ',',
  decimals = 0,
  decimal = '.',
  ...props
}) => {
  const [count, setCount] = useState(start);
  const countRef = useRef<HTMLSpanElement>(null);
  const startTimeRef = useRef<number | null>(null);
  const frameRef = useRef<number | null>(null);

  // Форматирование числа с разделителями и десятичными
  const formatNumber = (num: number): string => {
    return num.toLocaleString('ru-RU', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).replace(',', decimal).replace(/\s/g, separator);
  };

  // Анимация счета с использованием requestAnimationFrame
  useEffect(() => {
    const element = countRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting) {
          const animate = (timestamp: number) => {
            if (!startTimeRef.current) {
              startTimeRef.current = timestamp;
            }

            const elapsed = timestamp - startTimeRef.current;
            const progress = Math.min(elapsed / duration, 1);
            
            // Функция плавности (easeOutExpo)
            const easeOutExpo = (t: number): number => {
              return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
            };
            
            const easedProgress = easeOutExpo(progress);
            const currentCount = start + (end - start) * easedProgress;
            
            setCount(currentCount);
            
            if (progress < 1) {
              frameRef.current = requestAnimationFrame(animate);
            }
          };
          
          frameRef.current = requestAnimationFrame(animate);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    
    observer.observe(element);
    
    return () => {
      observer.disconnect();
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [start, end, duration]);

  return (
    <Text as="span" ref={countRef} {...props}>
      {prefix}{formatNumber(count)}{suffix}
    </Text>
  );
};

export default CountUp;