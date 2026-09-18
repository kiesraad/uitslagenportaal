import KiesraadGridHexagon from "@/elements/KiesraadGridHexagon.tsx";

export function HeroGrid() {
   return (
      <div className="-order-1 flex flex-col justify-center lg:order-0">
         <div className="flex justify-center pb-10 lg:pb-0 xl:pr-20">
            <img
               src="/images/homepage_img.webp"
               alt="Home hero"
               className="relative z-10 aspect-video max-h-80 w-full object-cover lg:aspect-11/12 lg:max-h-140 lg:max-w-2xl"
            />
         </div>
         <div className="hero-grid-container text-blue-500">
            <div className={"hero-grid-left"}>
               <div className={"hero-grid-v hero-grid"}>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
               </div>
               <div className={"hero-grid-v hero-grid"}>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
               </div>
            </div>
            <div className={"hero-grid-right"}>
               <div className={"hero-grid-h hero-grid"}>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
               </div>
               <div className={"hero-grid-h hero-grid"}>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
                  <div className={"hero-grid-item"}>
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                     <KiesraadGridHexagon className="hero-grid-item-bullet" />
                  </div>
               </div>
            </div>
         </div>
      </div>
   );
}
