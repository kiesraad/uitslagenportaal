import { fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import SearchAutocomplete, { type SearchListOption } from "@/components/SearchAutocomplete";
import { renderWithProviders } from "../testUtils";

const options: SearchListOption[] = [
   { id: "zoetermeer", label: "Zoetermeer" },
   { id: "zwolle", label: "Zwolle", content: <strong>Zwolle (Overijssel)</strong> },
   { id: "den-haag", label: "'s-Gravenhage", searchText: "Den Haag" },
];

function renderAutocomplete({ value = "z", isOpen = true as boolean | undefined } = {}) {
   const onChange = vi.fn();
   const onSelect = vi.fn();
   renderWithProviders(
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

// Holds the value like SearchBar does, leaving the open state to the component.
function Uncontrolled({ onOpenChange }: { onOpenChange?: (isOpen: boolean) => void }) {
   const [value, setValue] = useState("");
   return (
      <SearchAutocomplete
         label="Zoek gemeente"
         placeholder="Bijv. Zoetermeer"
         value={value}
         onChange={setValue}
         options={options}
         onSelect={(option) => setValue(option.label)}
         onOpenChange={onOpenChange}
      />
   );
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

   it("renders no listbox when nothing matches", () => {
      renderAutocomplete({ value: "xyz" });
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
   });

   it("lists the matching options, using their content when present", () => {
      renderAutocomplete({ value: "zw" });

      expect(screen.getByRole("listbox", { name: "Zoek gemeente" })).toBeInTheDocument();
      expect(screen.getAllByRole("option")).toHaveLength(1);
      expect(screen.getByRole("option", { name: "Zwolle (Overijssel)" })).toBeInTheDocument();
   });

   it("matches on search text as well as the label", () => {
      renderAutocomplete({ value: "den haag" });
      expect(screen.getByRole("option", { name: "'s-Gravenhage" })).toBeInTheDocument();
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

   it("opens on typing and closes on selection by itself", () => {
      const onOpenChange = vi.fn();
      renderWithProviders(<Uncontrolled onOpenChange={onOpenChange} />);
      const input = screen.getByRole("searchbox", { name: "Zoek gemeente" });

      fireEvent.change(input, { target: { value: "zw" } });
      expect(onOpenChange).toHaveBeenLastCalledWith(true);

      fireEvent.click(screen.getByRole("option", { name: "Zwolle (Overijssel)" }));
      expect(onOpenChange).toHaveBeenLastCalledWith(false);
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
      expect(input).toHaveValue("Zwolle");
   });

   it("closes on Enter without a highlighted suggestion", () => {
      const onOpenChange = vi.fn();
      renderWithProviders(<Uncontrolled onOpenChange={onOpenChange} />);
      const input = screen.getByRole("searchbox", { name: "Zoek gemeente" });
      fireEvent.change(input, { target: { value: "z" } });
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      fireEvent.keyDown(input, { key: "Enter" });

      expect(onOpenChange).toHaveBeenLastCalledWith(false);
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
   });

   it("selects rather than closes on Enter with a highlighted suggestion", () => {
      renderWithProviders(<Uncontrolled />);
      const input = screen.getByRole("searchbox", { name: "Zoek gemeente" });
      fireEvent.change(input, { target: { value: "zw" } });
      fireEvent.keyDown(input, { key: "ArrowDown" });

      fireEvent.keyDown(input, { key: "Enter" });
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      fireEvent.keyUp(input, { key: "Enter" });
      expect(input).toHaveValue("Zwolle");
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
   });

   it("announces the number of results while open", () => {
      renderWithProviders(<Uncontrolled />);
      const input = screen.getByRole("searchbox", { name: "Zoek gemeente" });

      expect(screen.getByRole("status")).toBeEmptyDOMElement();

      fireEvent.change(input, { target: { value: "z" } });
      expect(screen.getByRole("status")).toHaveTextContent("2 resultaten");

      fireEvent.change(input, { target: { value: "xyz" } });
      expect(screen.getByRole("status")).toHaveTextContent("Geen resultaten");
   });
});
