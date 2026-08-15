import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider"; // ← Fixed import
import { cn } from "@/lib/utils";

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(
  (
    { className, value, defaultValue, min = 0, max = 100, step = 1, ...props },
    ref
  ) => {
    return (
      <SliderPrimitive.Root
        ref={ref}
        value={value}
        defaultValue={defaultValue}
        min={min}
        max={max}
        step={step}
        className={cn(
          "relative flex w-full touch-none items-center select-none",
          className
        )}
        {...props}
      >
        {/* Track */}
        <SliderPrimitive.Track className="bg-muted border-border relative h-2 w-full grow overflow-hidden rounded-full border">
          {/* Filled Range */}
          <SliderPrimitive.Range className="bg-primary absolute h-full" />
        </SliderPrimitive.Track>

        {/* Thumbs */}
        {Array.from({
          length:
            Array.isArray(value) || Array.isArray(defaultValue)
              ? Array.isArray(value)
                ? value.length
                : defaultValue!.length
              : 1,
        }).map((_, index) => (
          <SliderPrimitive.Thumb
            key={index}
            className="border-secondary focus-visible:ring-ring bg-secondary block h-4 w-4 rounded-full border-2 shadow transition-all hover:scale-110 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50"
          />
        ))}
      </SliderPrimitive.Root>
    );
  }
);

Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
