import KiesraadGridHexagon from "@/elements/KiesraadGridHexagon.tsx";

export function HeroGrid() {
   return (
      <div className={"home-page-hero-right"}>
         <div className={"home-page-hero-img-container"}>
            <img src="/images/homepage_img.webp" alt="Home hero" className={"home-page-hero-img"} />
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
