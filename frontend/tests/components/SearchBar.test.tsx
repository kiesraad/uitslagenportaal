import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SearchBar from "@/components/SearchBar";
import { renderWithProviders } from "../testUtils";

const options = [
   { id: "zoetermeer", label: "Zoetermeer" },
   { id: "zoeterwoude", label: "Zoeterwoude" },
   { id: "zwolle", label: "Zwolle" },
];

function renderSearchBar(regionCategory: "GEMEENTE" | "STEMBUREAU" = "GEMEENTE") {
   const onSelect = vi.fn();
   renderWithProviders(<SearchBar regionCategory={regionCategory} options={options} onSelect={onSelect} />);
   return { onSelect, input: screen.getByRole("searchbox") };
}

describe("SearchBar", () => {
   it("names the input after its visible label", () => {
      renderSearchBar();
      expect(screen.getByRole("searchbox", { name: "Zoek gemeente" })).toBeInTheDocument();
   });

   it("exposes the suggestions as a listbox and announces how many there are", () => {
      const { input } = renderSearchBar();
      expect(input).not.toHaveAttribute("aria-controls");

      fireEvent.change(input, { target: { value: "zoeter" } });

      const listbox = screen.getByRole("listbox", { name: "Zoek gemeente" });
      expect(input).toHaveAttribute("aria-controls", listbox.id);
      expect(screen.getAllByRole("option")).toHaveLength(2);
      expect(screen.getByRole("status")).toHaveTextContent("2 resultaten");
   });

   it("announces when nothing matches", () => {
      const { input } = renderSearchBar();

      fireEvent.change(input, { target: { value: "xyz" } });

      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveTextContent("Geen resultaten");
   });

   it("selects the option highlighted with the arrow keys on Enter", () => {
      const { input, onSelect } = renderSearchBar();
      fireEvent.change(input, { target: { value: "zoeter" } });

      fireEvent.keyDown(input, { key: "ArrowDown" });
      fireEvent.keyDown(input, { key: "ArrowDown" });

      const highlighted = screen.getByRole("option", { name: "Zoeterwoude" });
      expect(input).toHaveAttribute("aria-activedescendant", highlighted.id);

      fireEvent.keyDown(input, { key: "Enter" });
      fireEvent.keyUp(input, { key: "Enter" });
      expect(onSelect).toHaveBeenCalledExactlyOnceWith(options[1]);
   });

   it("selects a clicked option", () => {
      const { input, onSelect } = renderSearchBar();
      fireEvent.change(input, { target: { value: "zw" } });

      fireEvent.click(screen.getByRole("option", { name: "Zwolle" }));

      expect(onSelect).toHaveBeenCalledExactlyOnceWith(options[2]);
      expect(input).toHaveValue("Zwolle");
   });

   it("submits only an exact match for a gemeente", () => {
      const { input, onSelect } = renderSearchBar();
      fireEvent.change(input, { target: { value: "zoeter" } });

      fireEvent.click(screen.getByRole("button", { name: "Zoeken" }));
      expect(onSelect).not.toHaveBeenCalled();

      fireEvent.change(input, { target: { value: "zoetermeer" } });
      fireEvent.click(screen.getByRole("button", { name: "Zoeken" }));
      expect(onSelect).toHaveBeenCalledExactlyOnceWith(options[0]);
   });

   it("submits the first match for a stembureau", () => {
      const { input, onSelect } = renderSearchBar("STEMBUREAU");
      fireEvent.change(input, { target: { value: "zoeter" } });

      fireEvent.click(screen.getByRole("button", { name: "Zoeken" }));

      expect(onSelect).toHaveBeenCalledExactlyOnceWith(options[0]);
   });
});
