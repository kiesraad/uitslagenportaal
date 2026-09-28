import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SearchAutocomplete, { type SearchListOption } from "@/components/SearchAutocomplete";

const options: SearchListOption[] = [
   { id: "zoetermeer", label: "Zoetermeer" },
   { id: "zwolle", label: "Zwolle", content: <strong>Zwolle (Overijssel)</strong> },
];

function renderAutocomplete({ value = "", isOpen = true } = {}) {
   const onChange = vi.fn();
   const onSelect = vi.fn();
   render(
      <SearchAutocomplete
         label="Zoek gemeente"
         placeholder="Bijv. Zoetermeer"
         value={value}
         onChange={onChange}
         options={options}
         isOpen={isOpen}
         onSelect={onSelect}
      />,
   );
   return { onChange, onSelect, input: screen.getByRole("searchbox", { name: "Zoek gemeente" }) };
}

describe("SearchAutocomplete", () => {
   it("shows the value and placeholder it is given", () => {
      const { input } = renderAutocomplete({ value: "zo" });
      expect(input).toHaveValue("zo");
      expect(input).toHaveAttribute("placeholder", "Bijv. Zoetermeer");
   });

   it("reports typed text", () => {
      const { input, onChange } = renderAutocomplete();

      fireEvent.change(input, { target: { value: "zw" } });

      expect(onChange).toHaveBeenCalledWith("zw");
   });

   it("renders no listbox while closed", () => {
      renderAutocomplete({ isOpen: false });
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
   });

   it("lists every option unfiltered, using its content when present", () => {
      renderAutocomplete({ value: "xyz" });

      expect(screen.getByRole("listbox", { name: "Zoek gemeente" })).toBeInTheDocument();
      expect(screen.getAllByRole("option")).toHaveLength(2);
      expect(screen.getByRole("option", { name: "Zwolle (Overijssel)" })).toBeInTheDocument();
   });

   it("selects a clicked option", () => {
      const { onSelect } = renderAutocomplete();

      fireEvent.click(screen.getByRole("option", { name: "Zwolle (Overijssel)" }));

      expect(onSelect).toHaveBeenCalledExactlyOnceWith(options[1]);
   });

   it("selects the option highlighted with the arrow keys on Enter", () => {
      const { input, onSelect } = renderAutocomplete();

      fireEvent.keyDown(input, { key: "ArrowDown" });
      expect(input).toHaveAttribute("aria-activedescendant", screen.getByRole("option", { name: "Zoetermeer" }).id);

      fireEvent.keyDown(input, { key: "Enter" });
      fireEvent.keyUp(input, { key: "Enter" });
      expect(onSelect).toHaveBeenCalledExactlyOnceWith(options[0]);
   });
});
